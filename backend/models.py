from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .constants import CONTENT_LENGTH_PRESETS, DEFAULT_CONFIG


class ConfigSection(BaseModel):
    api_key: str = ""
    model: str = DEFAULT_CONFIG["GROQ"]["model"]


class RedditSection(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    username: str = ""
    password: str = ""
    refresh_token: str = ""
    user_agent: str = DEFAULT_CONFIG["REDDIT"]["user_agent"]


class ConfigResponse(BaseModel):
    GROQ: ConfigSection
    REDDIT: RedditSection


class ConfigUpdate(BaseModel):
    GROQ: Optional[ConfigSection] = None
    REDDIT: Optional[RedditSection] = None


class GenerateRequest(BaseModel):
    keyword: Optional[str] = Field(default=None, description="Keyword filter for trending topics")
    tone: str = Field(default="Informative")
    region: str = Field(default="united_states")
    persona: str = Field(default="your witty social media co-pilot")
    length: str = Field(default="Standard")
    subreddit: Optional[str] = Field(default=None)
    auto_post: bool = Field(default=False)

    def clamp_length(self) -> str:
        if self.length not in CONTENT_LENGTH_PRESETS:
            return "Standard"
        return self.length


class GeneratedPost(BaseModel):
    topic: str
    title: str
    body: str
    link: str
    auto_posted: bool


class GenerateResponse(BaseModel):
    posts: List[GeneratedPost]
    message: str


class HistoryEntry(BaseModel):
    topic: str
    title: str
    subreddit: Optional[str]
    link: str
    upvotes: int
    comments: int
    timestamp: str


class HistoryResponse(BaseModel):
    items: List[HistoryEntry]


class ConversationEntry(BaseModel):
    id: str
    title: str
    persona: str
    tone: str
    updated_at: str


class ConversationHistory(BaseModel):
    conversation_id: str
    messages: List[Dict[str, str]]


class ConversationsResponse(BaseModel):
    conversations: List[ConversationEntry]


class StatsResponse(BaseModel):
    total_posts: int
    today_posts: int
    auto_posts: int


class MessageResponse(BaseModel):
    message: str
