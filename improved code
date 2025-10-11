import customtkinter as ctk
from tkinter import messagebox, filedialog, simpledialog
import webbrowser
import requests, json, csv, sqlite3, re, configparser, feedparser, threading, time, os
import praw
from datetime import datetime

# ─── Appearance Settings ───────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")

# Custom color palette
PRIMARY_BG        = ("#f8fafc", "#0f172a")
CARD_BG           = ("#e2e8f0", "#111827")
SECONDARY_BG      = ("#f1f5f9", "#172033")
TEXT_COLOR        = ("#0f172a", "#f8fafc")
ACCENT_COLOR      = "#38bdf8"
ACCENT_HOVER      = "#0ea5e9"
SUCCESS_COLOR     = "#34d399"
WARNING_COLOR     = "#facc15"
ERROR_COLOR       = "#f87171"

# ─── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_USER_AGENT = "taskpilot-agent/1.0"
CONFIG_FILE        = "taskpilot_config.ini"
DB_NAME            = "taskpilot.db"
UA_HEADERS         = {"User-Agent": "Mozilla/5.0"}
REGION_CODES       = {
    "united_states": "US", "united_kingdom": "GB",
    "japan": "JP", "germany": "DE", "australia": "AU"
}
REDIRECT_URI       = "http://localhost:8080"
GROQ_DEFAULT_MODEL = "llama-3.1-8b-instant"
GROQ_MODEL_CHOICES = [
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile",
    "llama-guard-3-8b",
    "gemma2-9b-it"
]
GROQ_DEPRECATED_MODELS = {
    "llama3-8b-8192": GROQ_DEFAULT_MODEL,
    "llama3-70b-8192": "llama-3.1-70b-versatile"
}

# ─── Default Configuration ─────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    'GROQ':    {'api_key': '',     'model': GROQ_DEFAULT_MODEL},
    'REDDIT': {
        'client_id':     '',
        'client_secret': '',
        'username':      '',
        'password':      '',
        'refresh_token': '',
        'user_agent':    DEFAULT_USER_AGENT
    }
}

# ─── Configuration Load/Save ───────────────────────────────────────────────────

def load_config():
    cfg = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        cfg.read_dict(DEFAULT_CONFIG)
        with open(CONFIG_FILE, 'w') as f:
            cfg.write(f)
    else:
        cfg.read(CONFIG_FILE)
        for section, defaults in DEFAULT_CONFIG.items():
            if section not in cfg:
                cfg[section] = {}
            for key, val in defaults.items():
                current = cfg[section].get(key, '').strip()
                if not current:
                    cfg[section][key] = val
    model_value = cfg['GROQ'].get('model', '').strip()
    if not model_value:
        cfg['GROQ']['model'] = GROQ_DEFAULT_MODEL
    elif model_value in GROQ_DEPRECATED_MODELS:
        cfg['GROQ']['model'] = GROQ_DEPRECATED_MODELS[model_value]
    return cfg

config = load_config()

# ─── UI Helpers ────────────────────────────────────────────────────────────────

app = None
status_var = None
history_stats_var = None
auto_post_var = None
progress_bar = None
history_box = None
results = None
groq_model_combo = None
persona_entry = None
length_var = None
stats_tiles = {}
nav_buttons = {}
tabs = None


def update_status(message):
    if status_var is None:
        return
    ui_call(status_var.set, message)


def update_stats_tiles(total_posts=0, today_posts=0, auto_refresh=0):
    if not stats_tiles:
        return
    ui_call(stats_tiles['total'].configure, text=f"{total_posts}\nTotal posts")
    ui_call(stats_tiles['today'].configure, text=f"{today_posts}\nToday")
    ui_call(stats_tiles['auto'].configure, text=f"{auto_refresh}\nAuto posts")


def switch_tab(name):
    if tabs is None:
        return
    tabs.set(name)
    for key, btn in nav_buttons.items():
        is_active = (key == name)
        fg = ACCENT_COLOR if is_active else "transparent"
        hover = ACCENT_HOVER if is_active else "#1f2937"
        text_color = "#0f172a" if is_active else "#cbd5f5"
        text = btn.cget("text")
        ui_call(btn.configure, fg_color=fg, hover_color=hover, text=text, text_color=text_color)


def ui_call(action, *args, **kwargs):
    if app and app.winfo_exists():
        app.after(0, lambda: action(*args, **kwargs))


def save_config():
    # GROQ
    config['GROQ']['api_key'] = groq_api_entry.get().strip()
    model_choice = groq_model_combo.get().strip() if groq_model_combo else ''
    if model_choice in GROQ_DEPRECATED_MODELS:
        model_choice = GROQ_DEPRECATED_MODELS[model_choice]
    config['GROQ']['model']   = model_choice or GROQ_DEFAULT_MODEL
    # REDDIT
    rd = config['REDDIT']
    rd['client_id']     = reddit_id_entry.get().strip()
    rd['client_secret'] = reddit_secret_entry.get().strip()
    rd['username']      = reddit_user_entry.get().strip()
    rd['password']      = reddit_pass_entry.get().strip()
    rd['refresh_token'] = reddit_refresh_entry.get().strip()
    rd['user_agent']    = reddit_agent_entry.get().strip() or DEFAULT_USER_AGENT
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)
    messagebox.showinfo("Saved", "Configuration updated.")

# ─── OAuth Refresh Token Flow ───────────────────────────────────────────────────

def obtain_refresh_token():
    client_id = reddit_id_entry.get().strip()
    if not client_id:
        messagebox.showerror("Error", "Client ID is required to get refresh token.")
        return
    reddit_app = praw.Reddit(
        client_id=client_id,
        client_secret=None,
        redirect_uri=REDIRECT_URI,
        user_agent=reddit_agent_entry.get().strip() or DEFAULT_USER_AGENT
    )
    auth_url = reddit_app.auth.url(scopes=["submit"], duration="permanent")
    webbrowser.open(auth_url)
    callback = simpledialog.askstring(
        "Authorization",
        "Visit the opened URL, authorize the app, then paste the full redirect URL here:"
    )
    if callback and "code=" in callback:
        code = callback.split("code=")[1]
        token = reddit_app.auth.authorize(code)
        reddit_refresh_entry.delete(0, 'end')
        reddit_refresh_entry.insert(0, token)
        messagebox.showinfo("Success", "Refresh token obtained. Save configuration.")
    else:
        messagebox.showwarning("Cancelled", "No authorization code found.")

# ─── Reddit Initialization & Validation ────────────────────────────────────────

reddit = None

def get_reddit_instance():
    rd = config['REDDIT']
    if rd.get('refresh_token'):
        return praw.Reddit(
            client_id=rd['client_id'],
            client_secret=None,
            refresh_token=rd['refresh_token'],
            redirect_uri=REDIRECT_URI,
            user_agent=rd['user_agent']
        )
    return praw.Reddit(
        client_id=rd['client_id'],
        client_secret=rd['client_secret'],
        username=rd['username'],
        password=rd['password'],
        user_agent=rd['user_agent']
    )

def validate_reddit():
    global reddit
    try:
        reddit = get_reddit_instance()
        me = reddit.user.me()
        messagebox.showinfo("Authenticated", f"Logged in as u/{me.name}")
        return True
    except Exception as e:
        messagebox.showerror("Auth Error", str(e))
        reddit = None
        return False

# ─── LLM Helpers ────────────────────────────────────────────────────────────────

def llm_request(prompt):
    key = config['GROQ']['api_key'].strip()
    model = config['GROQ']['model'].strip()
    if model in GROQ_DEPRECATED_MODELS:
        model = GROQ_DEPRECATED_MODELS[model]
    if not model:
        model = GROQ_DEFAULT_MODEL
    if not key:
        raise RuntimeError("Add your GROQ API key in Settings > Groq AI before generating posts.")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        res.raise_for_status()
    except requests.exceptions.HTTPError as err:
        detail = ""
        if err.response is not None:
            try:
                data = err.response.json()
                detail = data.get('error', {}).get('message') or data.get('message') or err.response.text
            except ValueError:
                detail = err.response.text
        detail = detail or str(err)
        raise RuntimeError(f"GROQ request failed: {detail}") from None
    except requests.exceptions.RequestException as err:
        raise RuntimeError(f"GROQ request failed: {err}") from None

    try:
        return res.json()['choices'][0]['message']['content'].strip()
    except (KeyError, IndexError, ValueError) as err:
        raise RuntimeError(f"Unexpected GROQ response format: {err}") from None

# ─── Post Generation & Database ─────────────────────────────────────────────────

CONTENT_LENGTH_PRESETS = {
    'Short': 3,
    'Standard': 5,
    'Extended': 7
}


def generate_post(topic, tone, region, persona, length_key):
    persona = persona or "a playful social media strategist"
    paragraphs = CONTENT_LENGTH_PRESETS.get(length_key, 5)
    title_prompt = (
        f"Craft a catchy, scroll-stopping Reddit post title for the topic '{topic}'. "
        f"Keep it under 18 words, target readers in {region.replace('_', ' ')} and match a {tone.lower()} vibe." 
        f"Include one relevant emoji if it boosts appeal."
    )
    title = llm_request(title_prompt)
    title_words = title.split()
    if len(title_words) > 18:
        title = ' '.join(title_words[:18])
    body_prompt = (
        f"You're {persona}. Create a lively Reddit self-post about '{topic}' for readers in {region.replace('_', ' ')}. "
        f"Use a {tone.lower()} tone, and deliver {paragraphs} vivid paragraphs. "
        f"Blend quick storytelling, one playful stat or fun fact, a social-media-style CTA, and a hashtag cluster at the end. "
        f"Sprinkle in markdown formatting (bold, italics, lists) where it enhances readability."
    )
    body = llm_request(body_prompt)
    return title.strip(), body.strip()

# Setup DB
with sqlite3.connect(DB_NAME) as db:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS posts(
            id INTEGER PRIMARY KEY,
            topic TEXT, title TEXT, body TEXT,
            region TEXT, tone TEXT,
            subreddit TEXT, link TEXT,
            upvotes INTEGER, comments INTEGER,
            timestamp TEXT
        )
        """
    )

# Log post
def log_post(topic, title, body, region, tone, subreddit, link):
    ts = datetime.now().isoformat()
    with sqlite3.connect(DB_NAME) as db:
        db.execute(
            "INSERT INTO posts(topic,title,body,region,tone,subreddit,link,upvotes,comments,timestamp)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (topic, title, body, region, tone, subreddit, link, 0, 0, ts)
        )
        db.commit()

# ─── Topic Fetching ─────────────────────────────────────────────────────────────

def fetch_json(url):
    resp = requests.get(url, headers=UA_HEADERS, timeout=10)
    clean = re.sub(r"^.*?\n", "", resp.text, count=1).strip()
    return json.loads(clean) if clean.startswith("{") else {}


def google_trends(region, keyword):
    geo = REGION_CODES.get(region, 'US')
    data = fetch_json(f"https://trends.google.com/trends/api/dailytrends?geo={geo}")
    days = data.get('default', {}).get('trendingSearchesDays', [])
    trends = [item['title']['query'] for d in days for item in d.get('trendingSearches', [])]
    if keyword:
        trends = [t for t in trends if keyword.lower() in t.lower()]
    return trends[:5]


def bing_news(keyword):
    rss_url = f"https://www.bing.com/news/search?q={requests.utils.quote(keyword or 'news')}&format=RSS"
    feed = feedparser.parse(rss_url)
    return [e.title for e in feed.entries][:5]


def get_topics(keyword, region):
    topics = google_trends(region, keyword)
    return topics if topics else bing_news(keyword)

# ─── Reddit Posting & Engagement ───────────────────────────────────────────────

def post_to_reddit(subreddit, title, body):
    if not reddit:
        raise RuntimeError("Not authenticated to Reddit.")
    submission = reddit.subreddit(subreddit).submit(title=title, selftext=body)
    return submission.url


def refresh_engagement():
    if not reddit:
        messagebox.showerror("Error", "Not authenticated.")
        return
    update_status("Syncing Reddit engagement...")
    with sqlite3.connect(DB_NAME) as db:
        for pid, link in db.execute("SELECT id, link FROM posts WHERE link LIKE '%reddit.com%'"):
            post = reddit.submission(url=link)
            db.execute(
                "UPDATE posts SET upvotes=?, comments=? WHERE id=?",
                (post.score, post.num_comments, pid)
            )
        db.commit()
    messagebox.showinfo("Updated", "Engagement stats refreshed.")
    refresh_history_view()
    update_status("Engagement stats refreshed.")

# ─── Summary & Export ──────────────────────────────────────────────────────────

def generate_daily_summary():
    today = datetime.now().date().isoformat()
    with sqlite3.connect(DB_NAME) as db:
        rows = db.execute(
            "SELECT topic,title,subreddit,link,upvotes,comments FROM posts WHERE DATE(timestamp)=?", (today,)
        ).fetchall()
    if not rows:
        return "No posts today."                        
    lines = [f"Daily Summary {today}"]
    for i,(t,ti,sub,lnk,up,com) in enumerate(rows,1):
        lines.append(f"{i}. {t} -> {ti}\n{sub}: {lnk}\n👍{up} 💬{com}\n")
    return "\n".join(lines)


def export_summary():
    txt = generate_daily_summary()
    path = filedialog.asksaveasfilename(defaultextension='.txt')
    if path:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(txt)
        messagebox.showinfo("Exported", "Summary saved.")


def export_csv():
    path = filedialog.asksaveasfilename(defaultextension='.csv')
    if path:
        with sqlite3.connect(DB_NAME) as db, open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID","Topic","Title","Body","Region","Tone","Subreddit","Link","Upvotes","Comments","Timestamp"])
            for row in db.execute("SELECT * FROM posts"):
                writer.writerow(row)
        messagebox.showinfo("Exported", "CSV saved.")


def refresh_history_view():
    if history_box is None:
        return
    with sqlite3.connect(DB_NAME) as db:
        rows = db.execute(
            "SELECT topic,title,subreddit,link,upvotes,comments,timestamp FROM posts ORDER BY timestamp DESC LIMIT 20"
        ).fetchall()
        total_posts = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        today = datetime.now().date().isoformat()
        today_posts = db.execute(
            "SELECT COUNT(*) FROM posts WHERE DATE(timestamp)=?", (today,)
        ).fetchone()[0]
        auto_posts = db.execute(
            "SELECT COUNT(*) FROM posts WHERE link LIKE 'http%' OR link LIKE 'https%'"
        ).fetchone()[0]

    def render():
        history_box.delete('0.0', 'end')
        if not rows:
            history_box.insert('end', "No posts logged yet. Run a generation to populate history.\n")
        else:
            for idx, (topic, title, subreddit, link, upvotes, comments, ts) in enumerate(rows, start=1):
                sub_line = subreddit or "(no subreddit)"
                history_box.insert(
                    'end',
                    f"{idx}. {topic}\n↳ {title}\n{sub_line} | {ts}\nLink: {link}\n👍 {upvotes}   💬 {comments}\n\n"
                )
        if history_stats_var is not None:
            history_stats_var.set(f"{total_posts} posts total · {today_posts} today")
        update_stats_tiles(total_posts, today_posts, auto_posts)

    ui_call(render)

# ─── Main Task Runner ─────────────────────────────────────────────────────────

def run_task(keyword, subreddit, tone, region, auto_post, persona, length_key):
    ui_call(results.delete, '0.0', 'end')
    ui_call(progress_bar.set, 0)
    update_status("Gathering fresh topics...")
    should_post = bool(subreddit and auto_post)
    if subreddit and not reddit and not validate_reddit():
        ui_call(results.insert, 'end', "❌ Reddit auth failed.\n")
        update_status("Reddit authentication failed.")
        return
    topics = get_topics(keyword, region)
    if not topics:
        ui_call(results.insert, 'end', "❌ No topics found.\n")
        update_status("No topics found for the current filters.")
        return

    total = len(topics)
    for idx, topic in enumerate(topics, start=1):
        try:
            title, body = generate_post(topic, tone, region, persona, length_key)
        except Exception as e:
            ui_call(results.insert, 'end', f"⚠ LLM error on '{topic}': {e}\n---\n")
            update_status(f"LLM error while crafting '{topic}'.")
            continue
        link = '[Skipped]'
        if should_post:
            try:
                link = post_to_reddit(subreddit, title, body)
            except Exception as e:
                link = f"Post failed: {e}"
        elif subreddit:
            link = "Posting disabled"
        log_post(topic, title, body, region, tone, subreddit, link)
        ui_call(results.insert, 'end', f"✅ {topic}: {title}\nLink: {link}\n\n{body}\n\n---\n")
        ui_call(results.see, 'end')
        ui_call(lambda value=idx/total: progress_bar.set(value))
        update_status(f"Completed {idx}/{total}: {topic}")
        ui_call(refresh_history_view)
        time.sleep(0.2)

    ui_call(progress_bar.set, 1)
    update_status("All done! Review the results pane.")


def start_task():
    params = dict(
        keyword=keyword_entry.get().strip(),
        subreddit=subreddit_entry.get().strip(),
        tone=tone_var.get(),
        region=region_var.get(),
        auto_post=auto_post_var.get(),
        persona=persona_entry.get().strip() if persona_entry else "",
        length_key=length_var.get() if length_var else 'Standard'
    )
    threading.Thread(target=run_task, kwargs=params, daemon=True).start()

# ─── UI Setup ─────────────────────────────────────────────────────────────────

app = ctk.CTk()
app.title("TaskPilot – Reddit Automation")
app.geometry("1024x780")
app.minsize(900, 700)
app.grid_columnconfigure(0, weight=0)
app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=0)
app.grid_rowconfigure(1, weight=1)
app.grid_rowconfigure(2, weight=0)
app.configure(fg_color=PRIMARY_BG)

heading_font = ctk.CTkFont(size=24, weight="bold")
subheading_font = ctk.CTkFont(size=13)


def handle_theme_change(choice):
    update_status(f"Theme switched to {choice} mode")
    mode = choice.lower()
    if mode == "system":
        ctk.set_appearance_mode("System")
    else:
        ctk.set_appearance_mode(mode)


def open_documentation():
    webbrowser.open("https://github.com/ZANYANBU/Taskpilot")


sidebar_frame = ctk.CTkFrame(app, corner_radius=18, fg_color="#0b1120")
sidebar_frame.grid(row=0, column=0, rowspan=3, sticky="nsw", padx=(15, 10), pady=10)
sidebar_frame.grid_rowconfigure(4, weight=1)

brand_label = ctk.CTkLabel(sidebar_frame, text="🛫 TaskPilot", font=ctk.CTkFont(size=24, weight="bold"), text_color="#f8fafc")
brand_label.grid(row=0, column=0, sticky="w", padx=20, pady=(24, 6))
brand_tagline = ctk.CTkLabel(
    sidebar_frame,
    text="Automate Reddit storytelling with trend-savvy prompts and mindful analytics.",
    wraplength=180,
    justify="left",
    text_color="#cbd5f5"
)
brand_tagline.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 16))

nav_group = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
nav_group.grid(row=2, column=0, sticky="ew", padx=10)
nav_group.grid_columnconfigure(0, weight=1)

nav_specs = [
    ("Generate", "⚡", 0),
    ("Settings", "⚙️", 1),
    ("History", "🗂", 2)
]

for name, icon, row in nav_specs:
    btn = ctk.CTkButton(
        nav_group,
        text=f"{icon}  {name}",
        anchor="w",
        fg_color="transparent",
        hover_color="#1f2937",
        text_color="#f8fafc",
        corner_radius=10,
        command=lambda n=name: switch_tab(n)
    )
    btn.grid(row=row, column=0, sticky="ew", pady=4)
    nav_buttons[name] = btn

stats_header = ctk.CTkLabel(sidebar_frame, text="Pulse", font=ctk.CTkFont(size=14, weight="bold"), text_color="#e2e8f0")
stats_header.grid(row=3, column=0, sticky="w", padx=20, pady=(20, 6))

stats_container = ctk.CTkFrame(sidebar_frame, fg_color="#101a33", corner_radius=16)
stats_container.grid(row=4, column=0, sticky="nsew", padx=15, pady=(0, 20))
stats_container.grid_columnconfigure(0, weight=1)

tile_specs = [
    ("total", "📈"),
    ("today", "🌞"),
    ("auto", "🤖")
]

for idx, (key, icon) in enumerate(tile_specs):
    tile = ctk.CTkFrame(stats_container, fg_color="transparent")
    tile.grid(row=idx, column=0, sticky="ew", padx=16, pady=8)
    icon_label = ctk.CTkLabel(tile, text=icon, font=ctk.CTkFont(size=20))
    icon_label.grid(row=0, column=0, padx=(0, 10))
    stats_label = ctk.CTkLabel(tile, text="0", justify="left", font=ctk.CTkFont(size=15, weight="bold"), text_color="#f8fafc")
    stats_label.grid(row=0, column=1, sticky="w")
    stats_tiles[key] = stats_label

support_button = ctk.CTkButton(
    sidebar_frame,
    text="Need help?",
    fg_color=ACCENT_COLOR,
    hover_color=ACCENT_HOVER,
    command=open_documentation
)
support_button.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 24))


header_frame = ctk.CTkFrame(app, corner_radius=0, fg_color=CARD_BG)
header_frame.grid(row=0, column=1, sticky="ew", padx=(0,15), pady=(10,0))
header_frame.grid_columnconfigure(0, weight=1)

title_label = ctk.CTkLabel(header_frame, text="TaskPilot Control Center", font=heading_font, text_color=TEXT_COLOR)
title_label.grid(row=0, column=0, sticky="w", padx=20, pady=(16, 0))
subtitle_label = ctk.CTkLabel(
    header_frame,
    text="Track trends, craft Reddit posts, and monitor engagement from a single dashboard.",
    font=subheading_font,
    text_color=TEXT_COLOR
)
subtitle_label.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 12))

theme_var = ctk.StringVar(value="Dark")
theme_switch = ctk.CTkSegmentedButton(
    header_frame,
    values=["Light", "Dark", "System"],
    command=handle_theme_change,
    variable=theme_var,
    fg_color=SECONDARY_BG,
    selected_color=ACCENT_COLOR
)
theme_switch.grid(row=0, column=1, rowspan=2, padx=20, pady=20, sticky="e")

docs_button = ctk.CTkButton(header_frame, text="Open Docs", width=110, command=open_documentation, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER)
docs_button.grid(row=0, column=2, rowspan=2, padx=(0, 20), pady=20)

body_frame = ctk.CTkFrame(app, corner_radius=18, fg_color=CARD_BG)
body_frame.grid(row=1, column=1, sticky="nsew", padx=(0, 15), pady=10)
body_frame.grid_rowconfigure(0, weight=1)
body_frame.grid_columnconfigure(0, weight=1)

tabs = ctk.CTkTabview(body_frame, fg_color=CARD_BG, segmented_button_fg_color=SECONDARY_BG, segmented_button_selected_color=ACCENT_COLOR)
tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

generate_tab = tabs.add("Generate")
settings_tab = tabs.add("Settings")
history_tab = tabs.add("History")

switch_tab("Generate")

if hasattr(tabs, "_segmented_button"):
    tabs._segmented_button.grid_remove()

# Generate Tab Layout
generate_tab.grid_columnconfigure(0, weight=1)
generate_tab.grid_columnconfigure(1, weight=1)
generate_tab.grid_rowconfigure(1, weight=1)

generate_intro = ctk.CTkLabel(
    generate_tab,
    text="Choose your parameters, then launch TaskPilot to assemble high-signal Reddit content.",
    anchor="w",
    text_color=TEXT_COLOR
)
generate_intro.grid(row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(18, 10))

controls_frame = ctk.CTkFrame(generate_tab, fg_color=SECONDARY_BG, corner_radius=12)
controls_frame.grid(row=1, column=0, sticky="nsew", padx=(24, 12), pady=(0, 20))
controls_frame.grid_columnconfigure(0, weight=1)

keyword_entry = ctk.CTkEntry(controls_frame, placeholder_text="Keyword focus (e.g. 'AI', 'markets')")
keyword_entry.grid(row=0, column=0, sticky="ew", pady=(0, 10))

subreddit_entry = ctk.CTkEntry(controls_frame, placeholder_text="Target subreddit (optional)")
subreddit_entry.grid(row=1, column=0, sticky="ew", pady=5)

filters_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
filters_frame.grid(row=2, column=0, sticky="ew", pady=5)
filters_frame.grid_columnconfigure((0, 1), weight=1)

tone_var = ctk.StringVar(value='Informative')
tone_menu = ctk.CTkOptionMenu(filters_frame, variable=tone_var, values=['Informative','Casual','Funny','Formal','Aggressive'], fg_color=ACCENT_COLOR, button_color=ACCENT_HOVER)
tone_menu.grid(row=0, column=0, sticky="ew", padx=(0, 6))

region_var = ctk.StringVar(value='united_states')
region_menu = ctk.CTkOptionMenu(filters_frame, variable=region_var, values=list(REGION_CODES.keys()), fg_color=ACCENT_COLOR, button_color=ACCENT_HOVER)
region_menu.grid(row=0, column=1, sticky="ew", padx=(6, 0))

personalize_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
personalize_frame.grid(row=3, column=0, sticky="ew", pady=(8, 4))
personalize_frame.grid_columnconfigure((0, 1), weight=1)

persona_entry = ctk.CTkEntry(personalize_frame, placeholder_text="Persona or voice (e.g. 'your witty social media co-pilot')")
persona_entry.insert(0, "your witty social media co-pilot")
persona_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

length_var = ctk.StringVar(value='Standard')
length_menu = ctk.CTkOptionMenu(
    personalize_frame,
    variable=length_var,
    values=list(CONTENT_LENGTH_PRESETS.keys()),
    fg_color=ACCENT_COLOR,
    button_color=ACCENT_HOVER
)
length_menu.grid(row=0, column=1, sticky="ew")

auto_post_var = ctk.BooleanVar(value=True)
auto_post_switch = ctk.CTkSwitch(
    controls_frame,
    text="Auto-post to Reddit when a subreddit is provided",
    variable=auto_post_var,
    progress_color=ACCENT_COLOR
)
auto_post_switch.grid(row=4, column=0, sticky="w", pady=(10, 6))

action_bar = ctk.CTkFrame(controls_frame, fg_color="transparent")
action_bar.grid(row=5, column=0, sticky="ew", pady=(6, 4))
action_bar.grid_columnconfigure(0, weight=1)

generate_button = ctk.CTkButton(action_bar, text="Generate Playbook", height=42, command=start_task, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER)
generate_button.grid(row=0, column=0, sticky="ew")


def clear_results():
    ui_call(results.delete, '0.0', 'end')
    ui_call(progress_bar.set, 0)
    update_status("Cleared previous run.")


clear_button = ctk.CTkButton(action_bar, text="Clear Results", width=140, command=clear_results, fg_color=SECONDARY_BG, hover_color="#1f2937", text_color=TEXT_COLOR)
clear_button.grid(row=0, column=1, padx=(10, 0))

output_frame = ctk.CTkFrame(generate_tab, corner_radius=12, fg_color=SECONDARY_BG)
output_frame.grid(row=1, column=1, sticky="nsew", padx=(12, 24), pady=(0, 20))
output_frame.grid_rowconfigure(1, weight=1)
output_frame.grid_columnconfigure(0, weight=1)

progress_bar = ctk.CTkProgressBar(output_frame)
progress_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
progress_bar.set(0)
progress_bar.configure(progress_color=ACCENT_COLOR)

results = ctk.CTkTextbox(output_frame, height=320, wrap='word')
results.configure(fg_color=PRIMARY_BG, text_color=TEXT_COLOR)
results.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

insights_frame = ctk.CTkFrame(generate_tab, fg_color="transparent")
insights_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 10))
insights_frame.grid_columnconfigure((0, 1, 2), weight=1)

insight_cards = [
    ("🧭 Creative prompt tip", "Blend persona tweaks with the Extended length preset for thought-leader vibes."),
    ("📰 Trending nudge", "Try leaving the keyword empty to scout Bing's freshest storylines."),
    ("📣 Engagement CTA", "Finish with a question + emojis to spark faster comment threads.")
]

for idx, (heading, copy) in enumerate(insight_cards):
    card = ctk.CTkFrame(insights_frame, corner_radius=12, fg_color=SECONDARY_BG)
    card.grid(row=0, column=idx, sticky="ew", padx=6)
    ctk.CTkLabel(card, text=heading, font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT_COLOR).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))
    ctk.CTkLabel(card, text=copy, wraplength=220, justify="left", text_color=TEXT_COLOR).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 16))

# Settings Tab Layout
settings_tab.grid_rowconfigure(0, weight=1)
settings_tab.grid_columnconfigure(0, weight=1)

settings_scroll = ctk.CTkScrollableFrame(settings_tab, label_text="Integrations & Credentials", corner_radius=12, fg_color=SECONDARY_BG)
settings_scroll.grid(row=0, column=0, sticky="nsew", padx=24, pady=20)
settings_scroll.grid_columnconfigure(0, weight=1)

groq_section_label = ctk.CTkLabel(settings_scroll, text="Groq AI", anchor="w", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_COLOR)
groq_section_label.grid(row=0, column=0, sticky="w", pady=(0, 8))

groq_api_entry = ctk.CTkEntry(settings_scroll, placeholder_text="Groq API Key")
groq_api_entry.insert(0, config['GROQ']['api_key'])
groq_api_entry.grid(row=1, column=0, sticky="ew", pady=5)

groq_model_combo = ctk.CTkComboBox(
    settings_scroll,
    values=GROQ_MODEL_CHOICES,
    justify="left",
    fg_color=ACCENT_COLOR,
    button_color=ACCENT_HOVER
)
groq_model_combo.set(config['GROQ']['model'])
groq_model_combo.grid(row=2, column=0, sticky="ew", pady=5)
ctk.CTkLabel(
    settings_scroll,
    text="Tip: pick a recommended model or type a valid Groq chat model name.",
    anchor="w",
    wraplength=420,
    text_color=TEXT_COLOR
).grid(row=3, column=0, sticky="w", pady=(0, 10))

reddit_section_label = ctk.CTkLabel(settings_scroll, text="Reddit OAuth", anchor="w", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_COLOR)
reddit_section_label.grid(row=4, column=0, sticky="w", pady=(10, 8))

reddit_id_entry = ctk.CTkEntry(settings_scroll, placeholder_text="Reddit Client ID")
reddit_id_entry.insert(0, config['REDDIT']['client_id'])
reddit_id_entry.grid(row=5, column=0, sticky="ew", pady=5)

reddit_secret_entry = ctk.CTkEntry(settings_scroll, placeholder_text="Client Secret", show='*')
reddit_secret_entry.insert(0, config['REDDIT']['client_secret'])
reddit_secret_entry.grid(row=6, column=0, sticky="ew", pady=5)

reddit_user_entry = ctk.CTkEntry(settings_scroll, placeholder_text="Username")
reddit_user_entry.insert(0, config['REDDIT']['username'])
reddit_user_entry.grid(row=7, column=0, sticky="ew", pady=5)

reddit_pass_entry = ctk.CTkEntry(settings_scroll, placeholder_text="Password", show='*')
reddit_pass_entry.insert(0, config['REDDIT']['password'])
reddit_pass_entry.grid(row=8, column=0, sticky="ew", pady=5)

reddit_refresh_entry = ctk.CTkEntry(settings_scroll, placeholder_text="Refresh Token")
reddit_refresh_entry.insert(0, config['REDDIT']['refresh_token'])
reddit_refresh_entry.grid(row=9, column=0, sticky="ew", pady=5)

reddit_agent_entry = ctk.CTkEntry(settings_scroll, placeholder_text="User Agent")
reddit_agent_entry.insert(0, config['REDDIT']['user_agent'])
reddit_agent_entry.grid(row=10, column=0, sticky="ew", pady=5)

settings_action_frame = ctk.CTkFrame(settings_scroll, fg_color="transparent")
settings_action_frame.grid(row=11, column=0, sticky="ew", pady=(10, 0))

ctk.CTkButton(settings_action_frame, text="Get Refresh Token", command=obtain_refresh_token).grid(row=0, column=0, padx=(0, 10))
ctk.CTkButton(settings_action_frame, text="Save & Validate", command=lambda: [save_config(), validate_reddit()]).grid(row=0, column=1)

# History Tab Layout
history_tab.grid_columnconfigure(0, weight=1)
history_tab.grid_rowconfigure(1, weight=1)

history_toolbar = ctk.CTkFrame(history_tab, fg_color="transparent")
history_toolbar.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
history_toolbar.grid_columnconfigure(3, weight=1)

ctk.CTkButton(history_toolbar, text="Refresh Engagement", command=refresh_engagement, fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER).grid(row=0, column=0, padx=(0, 10))
ctk.CTkButton(history_toolbar, text="Export Summary", command=export_summary, fg_color=SECONDARY_BG, hover_color="#1f2937", text_color=TEXT_COLOR).grid(row=0, column=1, padx=10)
ctk.CTkButton(history_toolbar, text="Export CSV", command=export_csv, fg_color=SECONDARY_BG, hover_color="#1f2937", text_color=TEXT_COLOR).grid(row=0, column=2, padx=10)

history_stats_var = ctk.StringVar(value="No posts yet.")
history_stats_label = ctk.CTkLabel(history_toolbar, textvariable=history_stats_var, anchor="e", text_color=TEXT_COLOR)
history_stats_label.grid(row=0, column=3, sticky="e")

history_box = ctk.CTkTextbox(history_tab, wrap='word')
history_box.configure(fg_color=PRIMARY_BG, text_color=TEXT_COLOR)
history_box.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))

status_var = ctk.StringVar(value="Ready to generate.")
status_bar = ctk.CTkLabel(app, textvariable=status_var, anchor="w", height=30, fg_color=CARD_BG, text_color=TEXT_COLOR)
status_bar.grid(row=2, column=1, sticky="ew", padx=(0, 15), pady=(0, 10))

refresh_history_view()

app.mainloop()
