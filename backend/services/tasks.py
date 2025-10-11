from __future__ import annotations

import time
from typing import List

from textwrap import shorten

from ..config import get_decrypted_config
from ..constants import CONTENT_LENGTH_PRESETS
from ..database import (
    add_message,
    create_conversation,
    fetch_style_samples,
    get_memory_context,
    log_post,
    update_conversation_timestamp,
)
from ..models import GenerateRequest, GeneratedPost
from .groq import GroqError
from .llm_providers import request_completion
from .reddit_service import RedditAuthError, get_reddit_client, post_to_reddit
from .topics import get_topics


def _normalize_snippet(text: str, width: int = 340) -> str:
    collapsed = " ".join(text.split())
    return shorten(collapsed, width=width, placeholder="…")


def _build_style_context(persona: str, conversation_id: str = "", limit: int = 5) -> str:
    samples = fetch_style_samples(limit)
    memory_samples = get_memory_context(persona, limit)

    blocks: List[str] = []

    # Add conversation memory if available
    if conversation_id:
        # Add recent conversation context
        conversation_blocks = []
        # This would be expanded to include actual conversation history
        # For now, we'll use memory context
        pass

    # Add memory context from similar personas
    if memory_samples:
        blocks.append("Recent conversation patterns:")
        for idx, (title, content, timestamp) in enumerate(memory_samples[:3], start=1):
            excerpt = _normalize_snippet(content or "")
            blocks.append(
                f"Memory {idx}: {title}\nExcerpt: {excerpt}"
            )

    # Add style samples from posts
    if samples:
        blocks.append("\nPrevious post styles:")
        for idx, (title, body, tone, persona_label) in enumerate(samples, start=1):
            persona_label = persona_label.strip() if persona_label and persona_label.strip() else "(persona not set)"
            excerpt = _normalize_snippet(body or "")
            blocks.append(
                f"Sample {idx}\n"
                f"Tone: {tone or 'unspecified'} | Persona: {persona_label}\n"
                f"Title: {title}\n"
                f"Excerpt: {excerpt}"
            )

    if not blocks:
        return ""

    return (
        "Study the user's established Reddit voice and conversation patterns below. Match their pacing, formatting, "
        "and energy while following new instructions. Learn from their conversation history to create more personalized content.\n\n"
        + "\n\n".join(blocks)
    )


def _build_title(topic: str, tone: str, region: str, persona: str, config, style_context: str) -> str:
    prompt_parts = []
    if style_context:
        prompt_parts.append(style_context)
    prompt_parts.append(
        f"Craft a catchy, scroll-stopping Reddit post title for the topic '{topic}'. "
        f"Keep it under 18 words, aim for readers in {region.replace('_', ' ')}, and match a {tone.lower()} vibe. "
        f"Lean into the persona '{persona}' if it adds flair, and include one relevant emoji only if it boosts appeal."
    )
    prompt = "\n\n".join(prompt_parts)
    title = request_completion(config["GROQ"]["api_key"], prompt, config["GROQ"]["model"]).split()
    if len(title) > 18:
        title = title[:18]
    return " ".join(title)


def _build_body(topic: str, tone: str, region: str, persona: str, paragraphs: int, config, style_context: str) -> str:
    prompt_parts = []
    if style_context:
        prompt_parts.append(style_context)
    prompt_parts.append(
        f"You're {persona or 'a playful social strategist'}. Create a lively Reddit self-post about '{topic}' for readers "
        f"in {region.replace('_', ' ')}. Use a {tone.lower()} tone and deliver {paragraphs} vivid paragraphs. Blend storytelling, "
        f"one playful stat or fun fact, a social-media-style CTA, and finish with a hashtag cluster. Utilize markdown (bold, italics, bullet points) "
        f"where it enhances readability. Make sure the voice is consistent with the style samples above."
    )
    prompt = "\n\n".join(prompt_parts)
    return request_completion(config["GROQ"]["api_key"], prompt, config["GROQ"]["model"])


def generate_posts(payload: GenerateRequest) -> List[GeneratedPost]:
    config = get_decrypted_config()
    topics = get_topics(payload.keyword or "", payload.region)
    if not topics:
        raise GroqError("No topics found for the current keyword/region filter.")

    # Create or continue conversation
    import uuid
    conversation_id = str(uuid.uuid4())
    create_conversation(conversation_id, f"Post Generation: {payload.keyword or 'General'}", payload.persona, payload.tone)

    # Add user intent as first message
    user_prompt = f"Generate Reddit posts about: {payload.keyword or 'current trends'} in {payload.region} with {payload.tone} tone as {payload.persona}"
    add_message(conversation_id, "user", user_prompt, f"region:{payload.region},tone:{payload.tone}")

    style_context = _build_style_context(payload.persona, conversation_id)

    reddit = None
    auto_post = bool(payload.auto_post and (payload.subreddit or "").strip())
    if auto_post:
        reddit = get_reddit_client(config["REDDIT"])
        if reddit is None:
            raise RedditAuthError("Reddit credentials are incomplete. Update them in Settings.")

    results: List[GeneratedPost] = []
    paragraphs = CONTENT_LENGTH_PRESETS.get(payload.clamp_length(), CONTENT_LENGTH_PRESETS["Standard"])

    for topic in topics:
        try:
            title = _build_title(topic, payload.tone, payload.region, payload.persona, config, style_context)
            body = _build_body(topic, payload.tone, payload.region, payload.persona, paragraphs, config, style_context)

            # Add assistant response to conversation
            assistant_content = f"Generated post - Title: {title}\n\nBody: {body}"
            add_message(conversation_id, "assistant", assistant_content, f"topic:{topic}")
        except GroqError:
            # propagate to caller to provide immediate feedback
            raise

        link = "[Skipped]"
        auto_flag = False
        if auto_post and reddit is not None:
            try:
                link = post_to_reddit(reddit, payload.subreddit.strip(), title, body)
                auto_flag = True
            except Exception as exc:  # keep generating other posts
                link = f"Post failed: {exc}"[:250]
                auto_flag = False

        log_post(
            topic=topic,
            title=title,
            body=body,
            region=payload.region,
            tone=payload.tone,
            persona=payload.persona,
            length=payload.clamp_length(),
            subreddit=payload.subreddit or "",
            link=link,
            auto_posted=auto_flag,
            conversation_id=conversation_id,
        )

        results.append(
            GeneratedPost(
                topic=topic,
                title=title,
                body=body,
                link=link,
                auto_posted=auto_flag,
            )
        )
        time.sleep(0.2)

    # Update conversation timestamp
    update_conversation_timestamp(conversation_id)

    return results
