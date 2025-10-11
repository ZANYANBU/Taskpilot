from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import get_decrypted_config, save_config
from .constants import BASE_DIR
from .database import (
    fetch_all_posts,
    fetch_posts_for_date,
    fetch_recent_posts,
    fetch_stats,
    get_conn,
    get_conversation_history,
    get_recent_conversations,
    init_db,
    iter_posts_for_refresh,
    update_metrics,
)
from .models import (
    ConfigResponse,
    ConfigUpdate,
    ConversationHistory,
    ConversationsResponse,
    GenerateRequest,
    GenerateResponse,
    GeneratedPost,
    HistoryEntry,
    HistoryResponse,
    MessageResponse,
    StatsResponse,
)
from .services.groq import GroqError
from .services.reddit_service import RedditAuthError, fetch_submission_stats, get_reddit_client
from .services.tasks import generate_posts

LOGGER = logging.getLogger("taskpilot.api")
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="TaskPilot API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    FRONTEND_DIR.mkdir(exist_ok=True)


# Static assets -------------------------------------------------------------
assets_dir = FRONTEND_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/", include_in_schema=False)
def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(index_path)


# Configuration -------------------------------------------------------------


@app.get("/api/config", response_model=ConfigResponse)
def get_config():
    cfg = get_decrypted_config()
    return ConfigResponse(
        GROQ={"api_key": cfg["GROQ"].get("api_key", ""), "model": cfg["GROQ"].get("model", "")},
        REDDIT={
            "client_id": cfg["REDDIT"].get("client_id", ""),
            "client_secret": cfg["REDDIT"].get("client_secret", ""),
            "username": cfg["REDDIT"].get("username", ""),
            "password": cfg["REDDIT"].get("password", ""),
            "refresh_token": cfg["REDDIT"].get("refresh_token", ""),
            "user_agent": cfg["REDDIT"].get("user_agent", ""),
        },
    )


@app.post("/api/config", response_model=MessageResponse)
def update_config(body: ConfigUpdate):
    payload: Dict[str, Dict[str, str]] = {}
    if body.GROQ is not None:
        payload["GROQ"] = body.GROQ.dict()
    if body.REDDIT is not None:
        payload["REDDIT"] = body.REDDIT.dict()
    if not payload:
        raise HTTPException(status_code=400, detail="No configuration fields supplied")
    save_config(payload)
    return MessageResponse(message="Configuration saved successfully.")


# Generation ---------------------------------------------------------------


@app.post("/api/generate", response_model=GenerateResponse)
def generate_content(body: GenerateRequest):
    try:
        posts = generate_posts(body)
    except GroqError as exc:
        LOGGER.exception("Groq error during generation")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RedditAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - catch-all safety
        LOGGER.exception("Unexpected error during generation")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return GenerateResponse(
        posts=[GeneratedPost(**post.dict()) for post in posts],
        message=f"Generated {len(posts)} posts.",
    )


# History & stats ----------------------------------------------------------


@app.get("/api/history", response_model=HistoryResponse)
def get_history(limit: int = 50):
    rows = fetch_recent_posts(limit)
    return HistoryResponse(
        items=[
            HistoryEntry(
                topic=row[0],
                title=row[1],
                subreddit=row[2],
                link=row[3],
                upvotes=row[4],
                comments=row[5],
                timestamp=row[6],
            )
            for row in rows
        ]
    )


@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    total, today, auto = fetch_stats()
    return StatsResponse(total_posts=total, today_posts=today, auto_posts=auto)


@app.get("/api/memory/stats")
def get_memory_stats():
    """Get memory and conversation analytics."""
    with get_conn() as conn:
        # Conversation stats
        conv_count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        msg_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

        # Recent activity
        recent_convs = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE updated_at >= datetime('now', '-7 days')"
        ).fetchone()[0]

        # Top personas
        top_personas = conn.execute(
            """
            SELECT persona, COUNT(*) as count
            FROM conversations
            GROUP BY persona
            ORDER BY count DESC
            LIMIT 5
            """
        ).fetchall()

        # Memory insights
        total_memory_items = conn.execute("SELECT COUNT(*) FROM messages WHERE role = 'assistant'").fetchone()[0]

    return {
        "conversations": conv_count,
        "messages": msg_count,
        "recent_activity": recent_convs,
        "top_personas": [{"persona": p[0], "count": p[1]} for p in top_personas],
        "memory_items": total_memory_items,
        "insights": [
            f"You've had {conv_count} conversation threads with the AI",
            f"Generated {msg_count} messages total",
            f"Most active persona: {top_personas[0][0] if top_personas else 'None'}",
            f"AI has {total_memory_items} memory items to learn from"
        ]
    }


@app.post("/api/refresh", response_model=MessageResponse)
def refresh_engagement():
    cfg = get_decrypted_config()
    reddit = get_reddit_client(cfg["REDDIT"])
    if reddit is None:
        raise HTTPException(status_code=400, detail="Reddit credentials missing. Add them in Settings.")

    updates = []
    for post_id, link in iter_posts_for_refresh():
        try:
            score, comments = fetch_submission_stats(reddit, link)
        except Exception as exc:
            LOGGER.warning("Failed to fetch stats for %s: %s", link, exc)
            continue
        updates.append((post_id, score, comments))

    update_metrics(updates)
    return MessageResponse(message=f"Updated {len(updates)} posts.")


@app.get("/api/summary")
def download_summary(format: str = "txt"):
    today = datetime.utcnow().date().isoformat()
    rows = fetch_posts_for_date(today)

    if format == "txt":
        if not rows:
            text = f"Daily Summary {today}\nNo posts recorded."
        else:
            lines = [f"Daily Summary {today}"]
            for idx, (topic, title, subreddit, link, upvotes, comments, timestamp) in enumerate(rows, start=1):
                lines.append(
                    f"{idx}. {topic} -> {title}\n{subreddit or '(no subreddit)'} | {timestamp}\n{link}\n👍 {upvotes} · 💬 {comments}\n"
                )
            text = "\n".join(lines)
        return PlainTextResponse(text, media_type="text/plain")

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "ID",
                "Topic",
                "Title",
                "Body",
                "Region",
                "Tone",
                "Persona",
                "Length",
                "Subreddit",
                "Link",
                "Upvotes",
                "Comments",
                "Timestamp",
            ]
        )
        for row in fetch_all_posts():
            writer.writerow(row)
        buffer.seek(0)
        headers = {"Content-Disposition": "attachment; filename=taskpilot-history.csv"}
        return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)

    raise HTTPException(status_code=400, detail="Unsupported format. Use txt or csv.")


# Conversation Memory Endpoints

@app.get("/api/conversations", response_model=ConversationsResponse)
def get_conversations(limit: int = 20):
    conversations = get_recent_conversations(limit)
    return ConversationsResponse(
        conversations=[
            {
                "id": conv[0],
                "title": conv[1],
                "persona": conv[2],
                "tone": conv[3],
                "updated_at": conv[4],
            }
            for conv in conversations
        ]
    )


@app.get("/api/conversations/{conversation_id}", response_model=ConversationHistory)
def get_conversation(conversation_id: str):
    messages = get_conversation_history(conversation_id)
    return ConversationHistory(
        conversation_id=conversation_id,
        messages=[
            {
                "role": msg[0],
                "content": msg[1],
                "timestamp": msg[2],
                "metadata": msg[3],
            }
            for msg in messages
        ]
    )
