"""
Reddit History Downloader - Main Application

Entry point for the Reddit scraper application with modular architecture.
Imports functionality from separate modules and provides the GUI.
"""

import customtkinter as ctk
import threading
import queue
import asyncio
import webbrowser

# Local imports
from config_manager import load_config, save_config, validate_credentials
from reddit_extractor import run_user_downloader_async, run_subreddit_downloader_async  
from ai_analyzer import run_ai_analysis_async


# --- GUI CLASS ---

class downloaderApp:
    # --- Stripe Light Theme Palette ---
    THEME_BG = "#F6F9FC"            # Light Blue-Gray Background
    THEME_CARD_BG = "#FFFFFF"       # Pure White Cards
    THEME_INPUT_BG = "#F6F9FC"      # Matches App Background for contrast
    THEME_ELEVATED_BG = "#FFFFFF"   # White for dropdowns
    THEME_ACCENT = "#0A2540"        # Navy Blue
    THEME_ACCENT_HOVER = "#153E60"  # Lighter Navy
    THEME_TEXT = "#0A2540"          # Dark Slate
    THEME_TEXT_SECONDARY = "#425466" # Slate
    THEME_PLACEHOLDER_TEXT = "#979DA2" # Standard Gray for placeholders
    THEME_SUCCESS = "#32D583"       # Vibrant Green
    THEME_ERROR = "#EF4444"         # Vibrant Red
    THEME_BORDER = "#E6E6E8"        # Light Gray Border

    def __init__(self, root):
        self.root = root
        self.root.title("KarmaScanner v1.0")
        self.root.geometry("1100x1000")
        self.msg_queue = queue.Queue()
        self.config = load_config()
        self.credentials_valid = False

        # --- Appearance ---
        ctk.set_appearance_mode("Light")
        self.root.configure(fg_color=self.THEME_BG)

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # --- Global Scrollable Frame ---
        self.main_scroll_frame = ctk.CTkScrollableFrame(self.root, fg_color="transparent")
        self.main_scroll_frame.grid(row=0, column=0, sticky="nsew")
        self.main_scroll_frame.grid_columnconfigure(0, weight=1)

        # --- Tabs ---
        self.tab_view = ctk.CTkTabview(self.main_scroll_frame, 
            fg_color=self.THEME_BG, 
            segmented_button_selected_color=self.THEME_ACCENT, 
            segmented_button_selected_hover_color=self.THEME_ACCENT_HOVER,
            segmented_button_unselected_color=self.THEME_CARD_BG,
            segmented_button_unselected_hover_color=self.THEME_BORDER,
            text_color=self.THEME_TEXT, 
            corner_radius=20,
            command=self.update_tab_colors)
        self.tab_view.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.tab_view.add("Settings")
        self.tab_view.add("User History")
        self.tab_view.add("Subreddit History")
        self.tab_view.add("Enhanced User Search")
        
        self.settings_tab = self.tab_view.tab("Settings")
        self.user_tab = self.tab_view.tab("User History")
        self.subreddit_tab = self.tab_view.tab("Subreddit History")
        self.enhanced_search_tab = self.tab_view.tab("Enhanced User Search")
        
        for tab in [self.settings_tab, self.user_tab, self.subreddit_tab, self.enhanced_search_tab]:
            tab.configure(fg_color=self.THEME_BG)

        # Set default tab
        self.tab_view.set("User History")

        # Initial color update for tabs
        self.update_tab_colors()

        self.create_settings_widgets()
        self.create_user_widgets()
        self.create_subreddit_widgets()
        self.create_enhanced_search_widgets()

        # --- Log Area ---
        self.log_area = ctk.CTkTextbox(self.main_scroll_frame, 
            state='disabled', 
            wrap='word', 
            fg_color=self.THEME_CARD_BG, 
            text_color=self.THEME_TEXT_SECONDARY,
            border_color=self.THEME_BORDER, 
            border_width=2,
            corner_radius=10,
            height=120,
            font=("Helvetica Neue", 12))
        # Increased padx to 40 to align with inner content cards (20 tab + 20 card)
        self.log_area.grid(row=1, column=0, padx=40, pady=(0, 20), sticky="nsew")

        self.process_queue()
        
        # Check if credentials are configured on startup
        self.check_initial_credentials()

    def update_tab_colors(self):
        """Updates the text color of tabs based on selection state."""
        selected_tab = self.tab_view.get()
        try:
            # Access internal segmented button's buttons to set individual text colors
            # This is a workaround as CTk doesn't support state-based text colors directly
            buttons = self.tab_view._segmented_button._buttons_dict
            for name, button in buttons.items():
                if name == selected_tab:
                    button.configure(text_color="#FFFFFF")
                else:
                    button.configure(text_color=self.THEME_TEXT)
        except Exception as e:
            print(f"Error updating tab colors: {e}")



    def create_settings_widgets(self):
        """Creates the Settings tab for API credentials configuration."""
        self.settings_tab.grid_columnconfigure(0, weight=1)
        
        # --- Header Card ---
        header_frame = ctk.CTkFrame(self.settings_tab, fg_color=self.THEME_CARD_BG, corner_radius=15, 
                                   border_width=2, border_color=self.THEME_BORDER)
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        header_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(header_frame, text="API Configuration", 
                    font=ctk.CTkFont(family="Helvetica Neue", size=18, weight="bold"),
                    text_color=self.THEME_TEXT).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        ctk.CTkLabel(header_frame, 
                    text="Configure your Reddit API credentials to use the downloader.", 
                    font=ctk.CTkFont(family="Helvetica Neue", size=13),
                    text_color=self.THEME_TEXT_SECONDARY).grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # --- Status Indicator ---
        status_frame = ctk.CTkFrame(self.settings_tab, fg_color=self.THEME_CARD_BG, corner_radius=15,
                                   border_width=2, border_color=self.THEME_BORDER)
        status_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        status_frame.grid_columnconfigure(1, weight=1)
        
        # Container for precise alignment
        status_container = ctk.CTkFrame(status_frame, fg_color="transparent")
        status_container.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        ctk.CTkLabel(status_container, text="Status:", 
                    font=ctk.CTkFont(family="Helvetica Neue", weight="bold"),
                    text_color=self.THEME_TEXT).grid(row=0, column=0, padx=(0, 10), pady=0)
        
        self.status_label = ctk.CTkLabel(status_container, text="Not Configured", 
                                        font=ctk.CTkFont(family="Helvetica Neue", weight="bold"),
                                        text_color=self.THEME_ERROR)
        self.status_label.grid(row=0, column=1, padx=0, pady=0)
        
        # --- API Credentials Form ---
        form_frame = ctk.CTkFrame(self.settings_tab, fg_color=self.THEME_CARD_BG, corner_radius=15,
                                 border_width=2, border_color=self.THEME_BORDER)
        form_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=0)
        form_frame.grid_columnconfigure(1, weight=1)
        
        # Client ID
        ctk.CTkLabel(form_frame, text="Client ID", text_color=self.THEME_TEXT).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.client_id_entry = ctk.CTkEntry(form_frame, placeholder_text="Enter your Client ID", 
                                           fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER, 
                                           corner_radius=10, height=40, text_color=self.THEME_TEXT)
        self.client_id_entry.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="ew")
        
        # Client Secret
        ctk.CTkLabel(form_frame, text="Client Secret", text_color=self.THEME_TEXT).grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.client_secret_entry = ctk.CTkEntry(form_frame, placeholder_text="Enter your Client Secret", 
                                               show="*", fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                               corner_radius=10, height=40, text_color=self.THEME_TEXT)
        self.client_secret_entry.grid(row=1, column=1, padx=20, pady=5, sticky="ew")
        
        # User Agent
        ctk.CTkLabel(form_frame, text="User Agent", text_color=self.THEME_TEXT).grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.user_agent_entry = ctk.CTkEntry(form_frame, placeholder_text="RedditHistoryDownloader/2.0", 
                                             fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                             corner_radius=10, height=40, text_color=self.THEME_TEXT)
        self.user_agent_entry.grid(row=2, column=1, padx=20, pady=5, sticky="ew")
        self.user_agent_entry.insert(0, "RedditHistoryDownloader/2.0")
        
        # Gemini API Key
        ctk.CTkLabel(form_frame, text="Gemini API Key", text_color=self.THEME_TEXT).grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.gemini_api_key_entry = ctk.CTkEntry(form_frame, placeholder_text="Enter your Gemini API Key (optional)", 
                                                 show="*", fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                 corner_radius=10, height=40, text_color=self.THEME_TEXT)
        self.gemini_api_key_entry.grid(row=3, column=1, padx=20, pady=5, sticky="ew")
        
        # --- Save Button ---
        self.save_button = ctk.CTkButton(form_frame, text="Save & Validate Credentials", 
                                        command=self.save_and_validate_credentials, 
                                        height=45, corner_radius=22,
                                        fg_color=self.THEME_ACCENT, hover_color=self.THEME_ACCENT_HOVER,
                                        font=ctk.CTkFont(family="Helvetica Neue", weight="bold"))
        self.save_button.grid(row=4, column=0, columnspan=2, padx=20, pady=25, sticky="ew")
        
        # --- Instructions ---
        instructions_frame = ctk.CTkFrame(self.settings_tab, fg_color=self.THEME_CARD_BG, corner_radius=15,
                                         border_width=2, border_color=self.THEME_BORDER)
        instructions_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(20, 10))
        instructions_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(instructions_frame, text="How to get Reddit API credentials", 
                    font=ctk.CTkFont(family="Helvetica Neue", weight="bold"),
                    text_color=self.THEME_TEXT).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        instructions_text = """1. Click the button below to open Reddit's app preferences page
2. Scroll down and click "create another app..." or "create an app..."
3. Fill out the form:
   - Name: Any name you want (e.g., "HistoryDownloader")
   - Type: Select "script"
   - Redirect URI: http://localhost:8080
4. Click "create app"
5. Copy the Client ID (under the app name) and Client Secret (labeled "secret")
6. Paste them above and click "Save & Validate Credentials"
"""
        ctk.CTkLabel(instructions_frame, text=instructions_text, 
                    text_color=self.THEME_TEXT_SECONDARY, justify="left",
                    font=ctk.CTkFont(family="Helvetica Neue", size=12)).grid(row=1, column=0, padx=20, pady=(0, 5), sticky="w")
        
        ctk.CTkButton(instructions_frame, text="Open Reddit App Preferences", 
                     command=lambda: webbrowser.open("https://www.reddit.com/prefs/apps"),
                     fg_color=self.THEME_INPUT_BG, border_color=self.THEME_ACCENT, 
                     border_width=1, hover_color=self.THEME_BG, text_color=self.THEME_ACCENT,
                     height=40, corner_radius=20).grid(row=2, column=0, padx=20, pady=(5, 20), sticky="ew")

    def create_user_widgets(self):
        self.user_tab.grid_columnconfigure(0, weight=1)

        # --- User Input Card ---
        user_frame = ctk.CTkFrame(self.user_tab, fg_color=self.THEME_CARD_BG, corner_radius=15,
                                 border_width=2, border_color=self.THEME_BORDER)
        user_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        user_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(user_frame, text="Target User", 
                    font=ctk.CTkFont(family="Helvetica Neue", size=16, weight="bold"),
                    text_color=self.THEME_TEXT).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 5), sticky="w")
        
        ctk.CTkLabel(user_frame, text="User history must be public.", 
                    font=ctk.CTkFont(family="Helvetica Neue", size=12),
                    text_color=self.THEME_TEXT_SECONDARY).grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="w")
        
        ctk.CTkLabel(user_frame, text="Username", text_color=self.THEME_TEXT).grid(row=2, column=0, padx=20, pady=(5, 20), sticky="w")
        self.user_entry = ctk.CTkEntry(user_frame, placeholder_text="e.g. spez", 
                                      fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                      corner_radius=10, height=40, text_color=self.THEME_TEXT)
        self.user_entry.grid(row=2, column=1, padx=20, pady=(5, 20), sticky="ew")

        # --- Filters Card ---
        filters_frame = ctk.CTkFrame(self.user_tab, fg_color=self.THEME_CARD_BG, corner_radius=15,
                                    border_width=2, border_color=self.THEME_BORDER)
        filters_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=0)
        filters_frame.grid_columnconfigure(1, weight=1)
        filters_frame.grid_columnconfigure(3, weight=1)

        # Post Filters Header
        ctk.CTkLabel(filters_frame, text="Post Filters", 
                    font=ctk.CTkFont(family="Helvetica Neue", weight="bold"),
                    text_color=self.THEME_TEXT).grid(row=0, column=0, columnspan=4, padx=20, pady=(20, 10), sticky="w")
        
        # Post Limits
        ctk.CTkLabel(filters_frame, text="Max posts", text_color=self.THEME_TEXT).grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.user_posts_limit_entry = ctk.CTkEntry(filters_frame, width=120, 
                                                  fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                  corner_radius=10, text_color=self.THEME_TEXT)
        self.user_posts_limit_entry.grid(row=1, column=1, padx=20, pady=5, sticky="w")

        # Post Scores
        ctk.CTkLabel(filters_frame, text="Min score", text_color=self.THEME_TEXT).grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.user_post_score_lower_entry = ctk.CTkEntry(filters_frame, width=120, 
                                                       fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                       corner_radius=10, text_color=self.THEME_TEXT)
        self.user_post_score_lower_entry.grid(row=2, column=1, padx=20, pady=5, sticky="w")
        
        ctk.CTkLabel(filters_frame, text="Max score", text_color=self.THEME_TEXT).grid(row=2, column=2, padx=20, pady=5, sticky="w")
        self.user_post_score_upper_entry = ctk.CTkEntry(filters_frame, width=120, 
                                                       fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                       corner_radius=10, text_color=self.THEME_TEXT)
        self.user_post_score_upper_entry.grid(row=2, column=3, padx=20, pady=5, sticky="w")

        # Post Text
        ctk.CTkLabel(filters_frame, text="Contains text", text_color=self.THEME_TEXT).grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.user_post_text_filter_entry = ctk.CTkEntry(filters_frame, placeholder_text="Filter by title/body", 
                                                       fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                       corner_radius=10, text_color=self.THEME_TEXT)
        self.user_post_text_filter_entry.grid(row=3, column=1, columnspan=3, padx=20, pady=5, sticky="ew")

        # Separator
        ctk.CTkFrame(filters_frame, height=1, fg_color=self.THEME_BORDER).grid(row=4, column=0, columnspan=4, sticky="ew", padx=20, pady=15)

        # Comment Filters Header
        ctk.CTkLabel(filters_frame, text="Comment Filters", 
                    font=ctk.CTkFont(family="Helvetica Neue", weight="bold"),
                    text_color=self.THEME_TEXT).grid(row=5, column=0, columnspan=4, padx=20, pady=5, sticky="w")

        # Comment Limits
        ctk.CTkLabel(filters_frame, text="Max comments", text_color=self.THEME_TEXT).grid(row=6, column=0, padx=20, pady=5, sticky="w")
        self.user_comments_limit_entry = ctk.CTkEntry(filters_frame, width=120, 
                                                     fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                     corner_radius=10, text_color=self.THEME_TEXT)
        self.user_comments_limit_entry.grid(row=6, column=1, padx=20, pady=5, sticky="w")

        # Comment Scores
        ctk.CTkLabel(filters_frame, text="Min score", text_color=self.THEME_TEXT).grid(row=7, column=0, padx=20, pady=5, sticky="w")
        self.user_comment_score_lower_entry = ctk.CTkEntry(filters_frame, width=120, 
                                                          fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                          corner_radius=10, text_color=self.THEME_TEXT)
        self.user_comment_score_lower_entry.grid(row=7, column=1, padx=20, pady=5, sticky="w")
        
        ctk.CTkLabel(filters_frame, text="Max score", text_color=self.THEME_TEXT).grid(row=7, column=2, padx=20, pady=5, sticky="w")
        self.user_comment_score_upper_entry = ctk.CTkEntry(filters_frame, width=120, 
                                                          fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                          corner_radius=10, text_color=self.THEME_TEXT)
        self.user_comment_score_upper_entry.grid(row=7, column=3, padx=20, pady=5, sticky="w")

        # Comment Text
        ctk.CTkLabel(filters_frame, text="Contains text", text_color=self.THEME_TEXT).grid(row=8, column=0, padx=20, pady=(5, 20), sticky="w")
        self.user_comment_text_filter_entry = ctk.CTkEntry(filters_frame, placeholder_text="Filter by comment body", 
                                                          fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                          corner_radius=10, text_color=self.THEME_TEXT)
        self.user_comment_text_filter_entry.grid(row=8, column=1, columnspan=3, padx=20, pady=(5, 20), sticky="ew")

        # --- Start Button ---
        self.start_user_button = ctk.CTkButton(self.user_tab, text="Start User History Download", 
                                              command=self.start_user_download, 
                                              height=45, corner_radius=22,
                                              fg_color=self.THEME_ACCENT, hover_color=self.THEME_ACCENT_HOVER,
                                              font=ctk.CTkFont(family="Helvetica Neue", weight="bold"))
        self.start_user_button.grid(row=2, column=0, padx=20, pady=(20, 0), sticky="ew")

    def create_subreddit_widgets(self):
        self.subreddit_tab.grid_columnconfigure(0, weight=1)

        # --- Subreddit Input Card ---
        sub_frame = ctk.CTkFrame(self.subreddit_tab, fg_color=self.THEME_CARD_BG, corner_radius=15,
                                border_width=2, border_color=self.THEME_BORDER)
        sub_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        sub_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(sub_frame, text="Target Subreddit", 
                    font=ctk.CTkFont(family="Helvetica Neue", size=16, weight="bold"),
                    text_color=self.THEME_TEXT).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")
        
        ctk.CTkLabel(sub_frame, text="Subreddit Name", text_color=self.THEME_TEXT).grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.subreddit_entry = ctk.CTkEntry(sub_frame, placeholder_text="e.g. Python", 
                                           fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                           corner_radius=10, height=40, text_color=self.THEME_TEXT)
        self.subreddit_entry.grid(row=1, column=1, sticky="ew", padx=20, pady=5)

        ctk.CTkLabel(sub_frame, text="Sort Method", text_color=self.THEME_TEXT).grid(row=2, column=0, padx=20, pady=(5, 20), sticky="w")
        self.sort_method = ctk.CTkComboBox(sub_frame, values=['Top', 'Hot', 'New', 'All'], 
                                          fg_color=self.THEME_ACCENT, border_width=0,
                                          corner_radius=10, height=40,
                                          button_color=self.THEME_ACCENT, button_hover_color=self.THEME_ACCENT_HOVER,
                                          text_color="#FFFFFF", dropdown_fg_color=self.THEME_ELEVATED_BG,
                                          dropdown_text_color=self.THEME_TEXT, state="readonly")
        self.sort_method.set('New')
        self.sort_method.grid(row=2, column=1, sticky="ew", padx=20, pady=(5, 20))

        # --- Filters Card ---
        filters_frame = ctk.CTkFrame(self.subreddit_tab, fg_color=self.THEME_CARD_BG, corner_radius=15,
                                    border_width=2, border_color=self.THEME_BORDER)
        filters_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=0)
        filters_frame.grid_columnconfigure(1, weight=1)
        filters_frame.grid_columnconfigure(3, weight=1)

        # Post Filters Header
        ctk.CTkLabel(filters_frame, text="Post Filters", 
                    font=ctk.CTkFont(family="Helvetica Neue", weight="bold"),
                    text_color=self.THEME_TEXT).grid(row=0, column=0, columnspan=4, padx=20, pady=(20, 10), sticky="w")
        
        # Post Limits
        ctk.CTkLabel(filters_frame, text="Max posts", text_color=self.THEME_TEXT).grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.subreddit_post_limit_entry = ctk.CTkEntry(filters_frame, width=120, 
                                                      fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                      corner_radius=10, text_color=self.THEME_TEXT)
        self.subreddit_post_limit_entry.grid(row=1, column=1, padx=20, pady=5, sticky="w")

        # Post Scores
        ctk.CTkLabel(filters_frame, text="Min score", text_color=self.THEME_TEXT).grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.subreddit_post_score_lower_entry = ctk.CTkEntry(filters_frame, width=120, 
                                                            fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                            corner_radius=10, text_color=self.THEME_TEXT)
        self.subreddit_post_score_lower_entry.grid(row=2, column=1, padx=20, pady=5, sticky="w")
        
        ctk.CTkLabel(filters_frame, text="Max score", text_color=self.THEME_TEXT).grid(row=2, column=2, padx=20, pady=5, sticky="w")
        self.subreddit_post_score_upper_entry = ctk.CTkEntry(filters_frame, width=120, 
                                                            fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                            corner_radius=10, text_color=self.THEME_TEXT)
        self.subreddit_post_score_upper_entry.grid(row=2, column=3, padx=20, pady=5, sticky="w")

        # Post Text
        ctk.CTkLabel(filters_frame, text="Contains text", text_color=self.THEME_TEXT).grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.subreddit_post_text_filter_entry = ctk.CTkEntry(filters_frame, placeholder_text="Filter by title/body", 
                                                            fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                            corner_radius=10, text_color=self.THEME_TEXT)
        self.subreddit_post_text_filter_entry.grid(row=3, column=1, columnspan=3, padx=20, pady=5, sticky="ew")

        # Separator
        ctk.CTkFrame(filters_frame, height=1, fg_color=self.THEME_BORDER).grid(row=4, column=0, columnspan=4, sticky="ew", padx=20, pady=15)

        # Comment Filters Header
        ctk.CTkLabel(filters_frame, text="Comment Filters", 
                    font=ctk.CTkFont(family="Helvetica Neue", weight="bold"),
                    text_color=self.THEME_TEXT).grid(row=5, column=0, columnspan=4, padx=20, pady=5, sticky="w")

        # Comment Scores
        ctk.CTkLabel(filters_frame, text="Min score", text_color=self.THEME_TEXT).grid(row=6, column=0, padx=20, pady=5, sticky="w")
        self.subreddit_comment_score_lower_entry = ctk.CTkEntry(filters_frame, width=120, 
                                                               fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                               corner_radius=10, text_color=self.THEME_TEXT)
        self.subreddit_comment_score_lower_entry.grid(row=6, column=1, padx=20, pady=5, sticky="w")
        
        ctk.CTkLabel(filters_frame, text="Max score", text_color=self.THEME_TEXT).grid(row=6, column=2, padx=20, pady=5, sticky="w")
        self.subreddit_comment_score_upper_entry = ctk.CTkEntry(filters_frame, width=120, 
                                                               fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                               corner_radius=10, text_color=self.THEME_TEXT)
        self.subreddit_comment_score_upper_entry.grid(row=6, column=3, padx=20, pady=5, sticky="w")

        # Comment Text
        ctk.CTkLabel(filters_frame, text="Contains text", text_color=self.THEME_TEXT).grid(row=7, column=0, padx=20, pady=(5, 20), sticky="w")
        self.subreddit_comment_text_filter_entry = ctk.CTkEntry(filters_frame, placeholder_text="Filter by comment body", 
                                                               fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                               corner_radius=10, text_color=self.THEME_TEXT)
        self.subreddit_comment_text_filter_entry.grid(row=7, column=1, columnspan=3, padx=20, pady=(5, 20), sticky="ew")

        # --- Start Button ---
        self.start_subreddit_button = ctk.CTkButton(self.subreddit_tab, text="Start Subreddit History Download", 
                                                   command=self.start_subreddit_download, 
                                                   height=45, corner_radius=22,
                                                   fg_color=self.THEME_ACCENT, hover_color=self.THEME_ACCENT_HOVER,
                                                   font=ctk.CTkFont(family="Helvetica Neue", weight="bold"))
        self.start_subreddit_button.grid(row=2, column=0, padx=20, pady=(20, 0), sticky="ew")

    def create_enhanced_search_widgets(self):
        """Creates the Enhanced User Search tab for AI-powered analysis."""
        self.enhanced_search_tab.grid_columnconfigure(0, weight=1)
        
        # --- Header Card ---
        header_frame = ctk.CTkFrame(self.enhanced_search_tab, fg_color=self.THEME_CARD_BG, corner_radius=15,
                                   border_width=2, border_color=self.THEME_BORDER)
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(header_frame, text="AI-Powered Analysis", 
                    font=ctk.CTkFont(family="Helvetica Neue", size=20, weight="bold"),
                    text_color=self.THEME_TEXT).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        ctk.CTkLabel(header_frame, 
                    text="Analyze a Reddit user's history with Google Gemini AI", 
                    font=ctk.CTkFont(family="Helvetica Neue", size=13),
                    text_color=self.THEME_TEXT_SECONDARY).grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # --- Input Card ---
        input_frame = ctk.CTkFrame(self.enhanced_search_tab, fg_color=self.THEME_CARD_BG, corner_radius=15,
                                  border_width=2, border_color=self.THEME_BORDER)
        input_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        input_frame.grid_columnconfigure(1, weight=1)
        
        # Username
        ctk.CTkLabel(input_frame, text="Username", text_color=self.THEME_TEXT).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.ai_username_entry = ctk.CTkEntry(input_frame, placeholder_text="e.g. spez", 
                                             fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                             corner_radius=10, height=40, text_color=self.THEME_TEXT)
        self.ai_username_entry.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="ew")
        
        # Time Period
        ctk.CTkLabel(input_frame, text="Time Period", text_color=self.THEME_TEXT).grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.time_period_selector = ctk.CTkComboBox(input_frame, 
                                                    values=['Last 7 days', 'Last 30 days', 'Last 3 months', 
                                                           'Last 6 months', 'Last 1 year', 'All time'],
                                                    fg_color=self.THEME_ACCENT, border_width=0,
                                                    corner_radius=10, height=40,
                                                    button_color=self.THEME_ACCENT, button_hover_color=self.THEME_ACCENT_HOVER,
                                                    text_color="#FFFFFF", dropdown_fg_color=self.THEME_ELEVATED_BG,
                                                    dropdown_text_color=self.THEME_TEXT, state="readonly")
        self.time_period_selector.set('Last 3 months')
        self.time_period_selector.grid(row=1, column=1, padx=20, pady=5, sticky="ew")
        
        # Question
        ctk.CTkLabel(input_frame, text="Your Question", text_color=self.THEME_TEXT).grid(row=2, column=0, padx=20, pady=(10, 5), sticky="nw")
        self.ai_question_textbox = ctk.CTkTextbox(input_frame, height=100, 
                                                  fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                  corner_radius=10, text_color=self.THEME_PLACEHOLDER_TEXT)
        self.ai_question_textbox.grid(row=2, column=1, padx=20, pady=(10, 5), sticky="ew")
        
        # Placeholder Logic
        self.ai_question_placeholder = "What are this user's main interests and topics they engage with?"
        self.ai_question_textbox.insert("1.0", self.ai_question_placeholder)
        
        def on_focus_in(event):
            if self.ai_question_textbox.get("1.0", "end-1c") == self.ai_question_placeholder:
                self.ai_question_textbox.delete("1.0", "end")
                self.ai_question_textbox.configure(text_color=self.THEME_TEXT)

        def on_focus_out(event):
            if not self.ai_question_textbox.get("1.0", "end-1c").strip():
                self.ai_question_textbox.insert("1.0", self.ai_question_placeholder)
                self.ai_question_textbox.configure(text_color=self.THEME_PLACEHOLDER_TEXT)

        self.ai_question_textbox.bind("<FocusIn>", on_focus_in)
        self.ai_question_textbox.bind("<FocusOut>", on_focus_out)
        
        # Analyze Button
        self.analyze_button = ctk.CTkButton(input_frame, text="Analyze User with AI", 
                                           command=self.start_ai_analysis, height=45, corner_radius=22,
                                           fg_color=self.THEME_ACCENT, hover_color=self.THEME_ACCENT_HOVER,
                                           font=ctk.CTkFont(family="Helvetica Neue", weight="bold"))
        self.analyze_button.grid(row=3, column=0, columnspan=2, padx=20, pady=20, sticky="ew")
        
        # --- Response Card ---
        response_frame = ctk.CTkFrame(self.enhanced_search_tab, fg_color=self.THEME_CARD_BG, corner_radius=15,
                                     border_width=2, border_color=self.THEME_BORDER)
        response_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        response_frame.grid_columnconfigure(0, weight=1)
        response_frame.grid_rowconfigure(1, weight=1)
        self.enhanced_search_tab.grid_rowconfigure(2, weight=1)
        
        ctk.CTkLabel(response_frame, text="AI Response", 
                    font=ctk.CTkFont(family="Helvetica Neue", weight="bold"),
                    text_color=self.THEME_TEXT).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        self.ai_response_textbox = ctk.CTkTextbox(response_frame, wrap='word', 
                                                  fg_color=self.THEME_INPUT_BG, border_width=1, border_color=self.THEME_BORDER,
                                                  corner_radius=10, text_color=self.THEME_TEXT, font=("Helvetica Neue", 13))
        self.ai_response_textbox.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.ai_response_textbox.insert("1.0", "AI analysis will appear here...")
        self.ai_response_textbox.configure(state='disabled')

    def check_initial_credentials(self):
        """Check if credentials exist and populate the form."""
        if self.config:
            self.client_id_entry.insert(0, self.config.get('client_id', ''))
            self.client_secret_entry.insert(0, self.config.get('client_secret', ''))
            user_agent = self.config.get('user_agent', 'RedditHistoryDownloader/2.0')
            self.user_agent_entry.delete(0, 'end')
            self.user_agent_entry.insert(0, user_agent)
        
        # Load Gemini API key if present
        gemini_api_key = self.config.get('gemini_api_key', '')
        if gemini_api_key:
            self.gemini_api_key_entry.insert(0, gemini_api_key)
        
        # Validate in background
            def validate_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                valid, message = loop.run_until_complete(
                    validate_credentials(
                        self.config.get('client_id', ''),
                        self.config.get('client_secret', ''),
                        user_agent
                    )
                )
                loop.close()
                
                if valid:
                    self.credentials_valid = True
                    self.status_label.configure(text="🟢 Connected", text_color=self.THEME_SUCCESS)
                    self.log_message("[SUCCESS] Credentials loaded and validated successfully!")
                else:
                    self.credentials_valid = False
                    self.status_label.configure(text="🔴 Invalid Credentials", text_color=self.THEME_ERROR)
                    self.log_message(f"[WARNING] Saved credentials are invalid: {message}")
                    self.log_message("[INFO] Please update your credentials in the Settings tab.")
                    self.disable_download_tabs()
            
            thread = threading.Thread(target=validate_async, daemon=True)
            thread.start()
        else:
            self.log_message("[INFO] No credentials found. Please configure your API credentials in the Settings tab.")
            self.disable_download_tabs()

    def save_and_validate_credentials(self):
        """Saves and validates the API credentials."""
        client_id = self.client_id_entry.get().strip()
        client_secret = self.client_secret_entry.get().strip()
        user_agent = self.user_agent_entry.get().strip() or "RedditHistoryDownloader/2.0"
        gemini_api_key = self.gemini_api_key_entry.get().strip()
        
        if not client_id or not client_secret:
            self.log_message("[ERROR] Please fill in both Client ID and Client Secret.")
            return
        
        self.log_message("[INFO] Validating credentials...")
        self.save_button.configure(state='disabled', text="⏳ Validating...")
        
        def validate_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            valid, message = loop.run_until_complete(
                validate_credentials(client_id, client_secret, user_agent)
            )
            loop.close()
            
            if valid:
                # Save to config
                if save_config(client_id, client_secret, user_agent, gemini_api_key):
                    self.config = load_config()
                    self.credentials_valid = True
                    self.status_label.configure(text="🟢 Connected", text_color=self.THEME_SUCCESS)
                    self.log_message(f"[SUCCESS] {message}")
                    self.log_message("[SUCCESS] Credentials saved successfully!")
                    self.enable_download_tabs()
                else:
                    self.log_message("[ERROR] Failed to save credentials to config.json")
            else:
                self.credentials_valid = False
                self.status_label.configure(text="🔴 Invalid Credentials", text_color=self.THEME_ERROR)
                self.log_message(f"[ERROR] {message}")
                self.disable_download_tabs()
            
            self.save_button.configure(state='normal', text="Save & Validate Credentials")
        
        thread = threading.Thread(target=validate_async, daemon=True)
        thread.start()

    def disable_download_tabs(self):
        """Disable User and Subreddit tabs when credentials are not configured."""
        self.start_user_button.configure(state='disabled')
        self.start_subreddit_button.configure(state='disabled')
    
    def enable_download_tabs(self):
        """Enable User and Subreddit tabs when credentials are valid."""
        self.start_user_button.configure(state='normal')
        self.start_subreddit_button.configure(state='normal')

    def log_message(self, message):
        self.log_area.configure(state='normal')
        self.log_area.insert(ctk.END, message + '\\n')
        self.log_area.configure(state='disabled')
        self.log_area.see(ctk.END)

    def process_queue(self):
        try:
            message = self.msg_queue.get_nowait()
            self.log_message(message)
            if "OPERATION COMPLETE" in message:
                self.enable_download_buttons()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)
    
    def _parse_int_value(self, value_str):
        """Converts a string to an integer, or None if invalid/empty."""
        if not value_str:
            return None
        try:
            return int(value_str)
        except ValueError:
            return None

    def disable_download_buttons(self):
        self.start_user_button.configure(state='disabled')
        self.start_subreddit_button.configure(state='disabled')

    def enable_download_buttons(self):
        if self.credentials_valid:
            self.start_user_button.configure(state='normal')
            self.start_subreddit_button.configure(state='normal')

    def start_user_download(self):
        if not self.credentials_valid:
            self.log_message("[ERROR] Please configure valid API credentials in the Settings tab first.")
            return
            
        username = self.user_entry.get().strip()
        if not username:
            self.log_message("[ERROR] Please enter a username.")
            return
        
        posts_limit = self._parse_int_value(self.user_posts_limit_entry.get())
        comments_limit = self._parse_int_value(self.user_comments_limit_entry.get())
        post_score_lower_threshold = self._parse_int_value(self.user_post_score_lower_entry.get())
        post_score_upper_threshold = self._parse_int_value(self.user_post_score_upper_entry.get())
        comment_score_lower_threshold = self._parse_int_value(self.user_comment_score_lower_entry.get())
        comment_score_upper_threshold = self._parse_int_value(self.user_comment_score_upper_entry.get())
        post_text_filter = self.user_post_text_filter_entry.get().strip()
        comment_text_filter = self.user_comment_text_filter_entry.get().strip()

        self.disable_download_buttons()
        self.log_message(f"--- STARTING USER DOWNLOADER FOR '{username}' ---")
        
        def thread_target():
            asyncio.run(run_user_downloader_async(username, posts_limit, comments_limit, post_score_lower_threshold, post_score_upper_threshold, comment_score_lower_threshold, comment_score_upper_threshold, post_text_filter, comment_text_filter, self.msg_queue, self.config))

        thread = threading.Thread(target=thread_target, daemon=True)
        thread.start()

    def start_subreddit_download(self):
        if not self.credentials_valid:
            self.log_message("[ERROR] Please configure valid API credentials in the Settings tab first.")
            return
            
        subreddit = self.subreddit_entry.get().strip()
        sort = self.sort_method.get().lower()
        if not subreddit:
            self.log_message("[ERROR] Please enter a subreddit name.")
            return
        
        post_limit = self._parse_int_value(self.subreddit_post_limit_entry.get())
        post_score_lower_threshold = self._parse_int_value(self.subreddit_post_score_lower_entry.get())
        post_score_upper_threshold = self._parse_int_value(self.subreddit_post_score_upper_entry.get())
        comment_score_lower_threshold = self._parse_int_value(self.subreddit_comment_score_lower_entry.get())
        comment_score_upper_threshold = self._parse_int_value(self.subreddit_comment_score_upper_entry.get())
        post_text_filter = self.subreddit_post_text_filter_entry.get().strip()
        comment_text_filter = self.subreddit_comment_text_filter_entry.get().strip()
            
        self.disable_download_buttons()
        self.log_message(f"--- STARTING SUBREDDIT DOWNLOADER FOR 'r/{subreddit}' (method: {sort}) ---")
        
        def thread_target():
            asyncio.run(run_subreddit_downloader_async(subreddit, sort, post_limit, post_score_lower_threshold, post_score_upper_threshold, comment_score_lower_threshold, comment_score_upper_threshold, post_text_filter, comment_text_filter, self.msg_queue, self.config))

        thread = threading.Thread(target=thread_target, daemon=True)
        thread.start()

    def start_ai_analysis(self):
        """Starts the AI analysis process for a Reddit user."""
        if not self.credentials_valid:
            self.log_message("[ERROR] Please configure valid Reddit API credentials in the Settings tab first.")
            return
        
        gemini_api_key = self.config.get('gemini_api_key', '').strip()
        if not gemini_api_key:
            self.log_message("[ERROR] Please configure your Gemini API key in the Settings tab first.")
            self.log_message("[INFO] Get a free API key at: https://makersuite.google.com/app/apikey")
            return
        
        username = self.ai_username_entry.get().strip()
        if not username:
            self.log_message("[ERROR] Please enter a username.")
            return
        
        question = self.ai_question_textbox.get("1.0", "end-1c").strip()
        if not question:
            self.log_message("[ERROR] Please enter a question.")
            return
        
        # Parse time period
        time_period_str = self.time_period_selector.get()
        time_period_map = {
            'Last 7 days': 7,
            'Last 30 days': 30,
            'Last 3 months': 90,
            'Last 6 months': 180,
            'Last 1 year': 365,
            'All time': 36500
        }
        days = time_period_map.get(time_period_str, 90)
        
        self.log_message(f"--- STARTING AI ANALYSIS FOR '{username}' ({time_period_str}) ---")
        self.analyze_button.configure(state='disabled', text="⏳ Analyzing...")
        self.ai_response_textbox.configure(state='normal')
        self.ai_response_textbox.delete("1.0", "end")
        self.ai_response_textbox.insert("1.0", "Gathering data and analyzing... This may take a minute...")
        self.ai_response_textbox.configure(state='disabled')
        
        def thread_target():
            try:
                # Run the async analysis
                result = asyncio.run(run_ai_analysis_async(
                    username, 
                    question, 
                    days, 
                    self.config, 
                    self.msg_queue
                ))
                
                # Update UI with result
                def update_ui():
                    self.ai_response_textbox.configure(state='normal')
                    self.ai_response_textbox.delete("1.0", "end")
                    self.ai_response_textbox.insert("1.0", result)
                    self.ai_response_textbox.configure(state='disabled')
                    self.analyze_button.configure(state='normal', text="Analyze User with AI")
                
                self.root.after(0, update_ui)
                
            except Exception as e:
                self.msg_queue.put(f"[ERROR] Analysis failed: {str(e)}")
                def reset_ui():
                    self.analyze_button.configure(state='normal', text="Analyze User with AI")
                self.root.after(0, reset_ui)

        thread = threading.Thread(target=thread_target, daemon=True)
        thread.start()

# --- APPLICATION START ---

if __name__ == "__main__":
    root = ctk.CTk()
    app = downloaderApp(root)
    root.mainloop()
