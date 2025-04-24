import customtkinter as ctk
from tkinter import messagebox, filedialog
import requests, json, csv, sqlite3, re, configparser, feedparser, threading, os, time
import praw
from datetime import datetime

# ─── Appearance ────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_USER_AGENT = "taskpilot-agent/1.0"
CONFIG_FILE        = "taskpilot_config.ini"
DB_NAME            = "taskpilot.db"
UA                 = {"User-Agent": "Mozilla/5.0"}
REGION_CODES       = {
    "united_states": "US", "united_kingdom": "GB",
    "japan": "JP", "germany": "DE", "australia": "AU"
}

# ─── Default Config ────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    'GROQ': {
        'api_key':    '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',
        'model':      'llama3-8b-8192'
    },
    'REDDIT': {
        'client_id':     '',
        'client_secret': '',
        'username':      '',
        'password':      '',
        'user_agent':    DEFAULT_USER_AGENT
    }
}

# ─── Load / Save Config ────────────────────────────────────────────────────────
def load_config():
    cfg = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        cfg.read_dict(DEFAULT_CONFIG)
        with open(CONFIG_FILE, "w") as f:
            cfg.write(f)
    else:
        cfg.read(CONFIG_FILE)
        for section, defaults in DEFAULT_CONFIG.items():
            if section not in cfg:
                cfg[section] = {}
            for key, val in defaults.items():
                cfg[section].setdefault(key, val)
    # ensure user_agent is never blank
    cfg['REDDIT'].setdefault('user_agent', DEFAULT_USER_AGENT)
    return cfg

config = load_config()

def save_config():
    # Groq
    config['GROQ']['api_key'] = groq_key_entry.get().strip() or DEFAULT_CONFIG['GROQ']['api_key']
    config['GROQ']['model']   = groq_model_entry.get().strip() or DEFAULT_CONFIG['GROQ']['model']
    # Reddit
    config['REDDIT']['client_id']     = reddit_id_entry.get().strip()
    config['REDDIT']['client_secret'] = reddit_secret_entry.get().strip()
    config['REDDIT']['username']      = reddit_user_entry.get().strip()
    config['REDDIT']['password']      = reddit_pass_entry.get().strip()
    ua = reddit_agent_entry.get().strip() or DEFAULT_USER_AGENT
    config['REDDIT']['user_agent']    = ua
    with open(CONFIG_FILE, "w") as f:
        config.write(f)
    messagebox.showinfo("Saved", "Credentials saved.")

# ─── PRAW Instance & Validation ───────────────────────────────────────────────
reddit = None

def get_reddit_instance():
    creds = config['REDDIT']
    ua = creds.get('user_agent') or DEFAULT_USER_AGENT
    return praw.Reddit(
        client_id=creds['client_id'],
        client_secret=creds['client_secret'],
        username=creds['username'],
        password=creds['password'],
        user_agent=ua
    )

def validate_reddit():
    global reddit
    try:
        reddit = get_reddit_instance()
        me = reddit.user.me()
        if me:
            messagebox.showinfo("Success", f"Authenticated as u/{me.name}")
            return True
        else:
            raise Exception("No user returned")
    except Exception as e:
        messagebox.showerror("Authentication Failed", f"{e}")
        reddit = None
        return False

# ─── LLM Helpers ───────────────────────────────────────────────────────────────
def llm_request(prompt):
    res = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {config['GROQ']['api_key']}",
            "Content-Type": "application/json"
        },
        json={"model": config['GROQ']['model'], "messages":[{"role":"user","content":prompt}]}
    )
    res.raise_for_status()
    return res.json()['choices'][0]['message']['content'].strip()

def generate_post(topic, tone, region):
    title_prompt = (
        f"You are a trending Reddit content creator. Create a catchy title (<20 words), "
        f"tone: {tone.lower()}, topic: '{topic}', region: {region}."
    )
    title = llm_request(title_prompt)
    if len(title.split()) > 20:
        raise ValueError("LLM returned >20 words title")
    body_prompt = (
        f"Write a 3-paragraph Reddit post in tone {tone.lower()}, region {region}, "
        f"based on this title: '{title}'."
    )
    body = llm_request(body_prompt)
    return title, body

# ─── Database ─────────────────────────────────────────────────────────────────
def setup_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                topic TEXT, title TEXT, body TEXT,
                region TEXT, tone TEXT,
                subreddit TEXT, link TEXT,
                upvotes INTEGER, comments INTEGER,
                timestamp TEXT
            )
        """)

def log_post(topic, title, body, region, tone, subreddit, link):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            INSERT INTO posts 
            (topic, title, body, region, tone, subreddit, link, upvotes, comments, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
        """, (topic, title, body, region, tone, subreddit, link, datetime.now().isoformat()))
        conn.commit()

# ─── Trending Fetchers ─────────────────────────────────────────────────────────
def fetch_json(url):
    resp  = requests.get(url, headers=UA, timeout=10)
    clean = re.sub(r"^.*?\n", "", resp.text, count=1).strip()
    return json.loads(clean) if clean.startswith("{") else {}

def google_trends(region, keyword):
    geo = REGION_CODES.get(region, "US")
    try:
        url   = f"https://trends.google.com/trends/api/dailytrends?geo={geo}"
        data  = fetch_json(url)
        return [itm['title']['query'] for day in data.get('default', {}).get('trendingSearchesDays', []) for itm in day.get('trendingSearches', [])][:5]
    except:
        return []

def bing_news(keyword):
    rss  = f"https://www.bing.com/news/search?q={requests.utils.quote(keyword or 'news')}&format=RSS"
    feed = feedparser.parse(rss)
    return [e.title for e in feed.entries][:5]

def get_topics(keyword, region):
    topics = google_trends(region, keyword)
    return topics or bing_news(keyword)

# ─── Posting & Engagement ─────────────────────────────────────────────────────
def post_to_reddit(subreddit, title, body):
    if reddit is None:
        raise RuntimeError("Reddit not authenticated")
    try:
        submission = reddit.subreddit(subreddit).submit(title=title[:290], selftext=body)
        return submission.url
    except AttributeError as e:
        # Skip if user_agent fallback wasn’t applied correctly (_NotSet error)
        if "_NotSet" in str(e):
            return "[Skipped: missing or invalid user_agent]"
        raise
    except praw.exceptions.RedditAPIException as e:
        # Handle rate limits or other API errors
        return f"[Reddit API Error: {e}]"
    except Exception as e:
        return f"[Unexpected Reddit Error: {e}]"
def refresh_engagement():
    if reddit is None:
        messagebox.showerror("Error", "Not authenticated")
        return
    with sqlite3.connect(DB_NAME) as conn:
        for pid, link in conn.execute("SELECT id, link FROM posts WHERE link LIKE '%reddit.com%'"):
            post = reddit.submission(url=link)
            conn.execute("UPDATE posts SET upvotes=?, comments=? WHERE id=?", (post.score, post.num_comments, pid))
        conn.commit()
    messagebox.show
