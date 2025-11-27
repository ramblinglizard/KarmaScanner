"""
Configuration Manager Module

Handles loading, saving, and validating API credentials for Reddit and Gemini AI.
Credentials are stored in config.json file.
"""

import json
import os
import asyncpraw as praw
import google.generativeai as genai


CONFIG_FILE = "config.json"


def load_config():
    """Loads API credentials from config.json file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
    return {}


def save_config(client_id, client_secret, user_agent, gemini_api_key=""):
    """Saves API credentials to config.json file."""
    # Load existing config to preserve other fields
    existing_config = load_config()
    
    config = {
        "client_id": client_id,
        "client_secret": client_secret,
        "user_agent": user_agent,
        "gemini_api_key": gemini_api_key if gemini_api_key else existing_config.get("gemini_api_key", "")
    }
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


async def validate_credentials(client_id, client_secret, user_agent):
    """Validates Reddit API credentials by attempting a connection."""
    reddit = None
    try:
        reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
        await reddit.user.me()
        return True, "Credentials are valid!"
    except Exception as e:
        return False, f"Invalid credentials: {str(e)}"
    finally:
        if reddit:
            await reddit.close()


def validate_gemini_api_key(api_key):
    """Validates Gemini API key by attempting a simple request."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("test")
        return True, "Gemini API key is valid!"
    except Exception as e:
        return False, f"Invalid Gemini API key: {str(e)}"
