# Taskpilot


---

# 🚀 Taskpilot

**AI-Powered Reddit Automation and Analytics Tool**
Built by [V Anbu Chelvan](https://github.com/ZANYANBU)

Taskpilot is a smart desktop app that automates Reddit content creation, posting, and tracking using AI. With Groq's Gemini LLM, real-time trend tracking, and a clean user interface, Taskpilot is designed for content creators, marketers, and researchers who want to save time and boost productivity.

---

## 🌟 Features

* 🤖 **AI Post Generation**: Uses Groq’s Gemini LLM to generate Reddit posts based on custom prompts, tones, and topics.
* 🌐 **Reddit Automation**: Seamlessly post content to selected subreddits using the PRAW API.
* 📈 **Trend Tracking**: Fetches trending topics from Bing, Google, and Reddit to stay ahead of the curve.
* 🧠 **Customizable Tone**: Choose the tone of your posts (professional, casual, sarcastic, etc.).
* 🗃 **Post History & Analytics**: Stores all posts in a local SQLite database with options to export to CSV.
* 🖥 **User-Friendly GUI**: Clean and responsive interface built with `CustomTkinter`.
* 📝 **Daily Summary**: Keeps track of daily activity and performance.

---

## 🔧 Tech Stack

| Component     | Tech Used         |
| ------------- | ----------------- |
| Programming   | Python 3.10+      |
| GUI Framework | CustomTkinter     |
| AI Model      | Groq (Gemini LLM) |
| Reddit API    | PRAW              |
| Database      | SQLite            |
| Data Export   | CSV               |

---

## 📷 Screenshots

> *Include some screenshots here of the GUI, post generation, and analytics (optional but recommended).*

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10 or above
* Groq API Key
* Reddit Developer Credentials (Client ID & Secret)

### Installation

```bash
git clone https://github.com/ZANYANBU/Taskpilot.git
cd Taskpilot
pip install -r requirements.txt
```

### Configuration

Create a `.env` file or configure `auth.py` with:

```python
GROQ_API_KEY = "your_api_key_here"
REDDIT_CLIENT_ID = "your_client_id"
REDDIT_SECRET = "your_secret"
REDDIT_USERNAME = "your_username"
REDDIT_PASSWORD = "your_password"
```

### Run the App

```bash
python main.py
```

---

## 📦 Folder Structure

```
Taskpilot/
├── main.py
├── ui/                  # GUI layout and components
├── ai/                  # AI generation logic (Groq integration)
├── reddit/              # Reddit posting and PRAW integration
├── data/                # SQLite and CSV logging
├── utils/               # Helper functions
├── assets/              # Icons and images
└── requirements.txt
```

---

## 🎓 Author

**V Anbu Chelvan**
*First-year Computer Science student passionate about AI, automation, and real-world problem solving.*
🔗 [GitHub](https://github.com/ZANYANBU)

---

## 🛡️ License

This project is licensed under the [MIT License](LICENSE).

---

## 🙌 Contributing

Pull requests are welcome! If you have suggestions or improvements, feel free to fork the repo and submit a PR.

---

