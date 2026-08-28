# 🚀 BigQuery Release Notes Tracker

A modern, fast web application built with **Python Flask** and vanilla **HTML, CSS, and JavaScript** that fetches live Google Cloud BigQuery release notes from the official XML feed (`https://docs.cloud.google.com/feeds/bigquery-release-notes.xml`) and lets you easily read, search, filter, and Tweet/share any specific update.

---

## ✨ Features

- **Live XML Feed Fetching & Parsing**: Pulls real-time Atom XML updates from Google Cloud BigQuery docs and breaks them down by release date and category (Features, Security, Changes, Bug Fixes, Deprecations).
- **Refresh with Loading Spinner**: One-click refresh button with a smooth spinner animation to instantly fetch new updates or bust cache.
- **Search & Category Filtering**: Instant client-side search across all updates and filter pills (Feature, Security, Changed, Fixed, Deprecated).
- **Tweet Any Update on 𝕏 / Twitter**:
  - Click **Tweet** on any specific update to open a dedicated tweet composer modal preloaded with a formatted summary, hashtags, and direct link.
  - Live character counter (280 max) with hashtag quick-add buttons.
  - Multi-select support: Select multiple updates using checkboxes to compose a combined update tweet.
- **One-Click Clipboard Copying**: Easily copy update text or composed tweets with toast notifications.
- **Modern & Responsive UI**: Clean Google Cloud / BigQuery dark-themed design built with semantic HTML and CSS (no bulky JS frameworks needed).

---

## 🛠️ Quick Start

### 1. Navigate to the project directory
```bash
cd C:\Users\aletz\agy-cli-projects\bigquery-release-tracker
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Flask application
```bash
python app.py
```

### 4. Open in your browser
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 📂 Project Structure

```
bigquery-release-tracker/
├── app.py                  # Flask backend & Atom XML feed parser with caching
├── requirements.txt        # Python dependencies (Flask, requests, beautifulsoup4)
├── README.md               # Documentation & setup instructions
├── templates/
│   └── index.html          # Clean HTML5 interface
└── static/
    ├── css/
    │   └── style.css       # Custom responsive CSS styling & animations
    └── js/
        └── app.js          # Vanilla JS feed loader, search, filters & tweet composer
```
