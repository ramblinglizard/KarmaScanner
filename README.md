# KarmaScanner v1.0 🚀

**The Ultimate AI-Powered Reddit Analysis Tool**

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Stable-success?style=for-the-badge)]()

**KarmaScanner** is a cutting-edge desktop application designed to unlock the secrets hidden within Reddit history. Whether you are a data analyst, a researcher, or just curious, KarmaScanner empowers you to download, filter, and **analyze Reddit data using the power of Google Gemini AI**.

---

## ✨ Why KarmaScanner?

KarmaScanner isn't just a downloader; it's an intelligent insight engine.

- **🧠 AI-Powered Insights**: Don't just read comments—understand them. Ask questions like _"What are this user's main interests?"_ or _"Is this user an expert in Python?"_ and let Google Gemini AI provide a detailed analysis based on their history.
- **🎨 Stunning Modern UI**: Built with a **Stripe-inspired aesthetic**, featuring a clean, responsive design, dark/light mode support (optimized for Light mode), and a buttery-smooth user experience.
- **🔍 Surgical Precision**: Filter content by **score**, **keywords**, **date**, or **subreddit**. Find exactly what you're looking for without the noise.
- **🛡️ Privacy First**: Your API credentials are stored locally and securely. No data is ever sent to third-party servers other than Reddit, and optionally Google (if you want to perform AI analysis).

---

## 🚀 Key Features

### 🤖 Enhanced User Search (AI)

- **Deep Profiling**: Analyze a user's entire public history.
- **Custom Queries**: Ask specific questions about the user's behavior, expertise, or sentiment.
- **Gemini Integration**: Leverages Google's advanced Gemini Pro model for human-like understanding.

### 📥 Comprehensive Downloader

- **User History**: Scrape thousands of posts and comments from any public profile.
- **Subreddit History**: Download top, new, or hot posts from any community.
- **JSON Export**: All data is saved in structured, machine-readable JSON files for further analysis.

### 🎛️ Advanced Filtering

- **Score Thresholds**: Ignore low-effort content by setting minimum upvote limits.
- **Keyword Search**: Filter posts and comments that contain specific phrases.
- **Limit Controls**: Define exactly how many items to retrieve to respect API limits.

---

## 🛠️ Installation

Get up and running in minutes.

### Prerequisites

- Python 3.7 or higher
- A Reddit Account (for API credentials)
- (Optional) Google Cloud Account (for Gemini API)

### Quick Start

1.  **Clone the repository**

    ```bash
    git clone https://github.com/yourusername/KarmaScanner.git
    cd KarmaScanner
    ```

2.  **Install dependencies**

    ```bash
    pip install customtkinter asyncpraw google-generativeai
    ```

3.  **Launch the App**
    ```bash
    python main.py
    ```

---

## ⚙️ Configuration

KarmaScanner features a built-in **Settings GUI** to manage your credentials easily.

1.  **Reddit API**:

    - Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).
    - Create a **script** app.
    - Copy the `Client ID` and `Client Secret` into KarmaScanner's Settings tab.

2.  **Google Gemini API** (Optional):
    - Get your key from [Google AI Studio](https://makersuite.google.com/app/apikey).
    - Paste it into the Settings tab to unlock AI features.


## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

_Keywords: Reddit Scraper, Reddit Analysis, OSINT Tool, AI Analysis, Google Gemini, Python GUI, Data Mining, Social Media Analysis, KarmaScanner_
