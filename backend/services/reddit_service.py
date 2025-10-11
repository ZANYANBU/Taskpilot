from functools import lru_cache
from typing import Optional

import praw

from ..constants import REDIRECT_URI


class RedditAuthError(RuntimeError):
    """Raised when Reddit authentication fails."""


@lru_cache(maxsize=1)
def _build_reddit(**credentials) -> praw.Reddit:
    return praw.Reddit(**credentials)


def get_reddit_client(config_section) -> Optional[praw.Reddit]:
    client_id = config_section.get("client_id", "").strip()
    user_agent = config_section.get("user_agent", "").strip()
    refresh_token = config_section.get("refresh_token", "").strip()
    client_secret = config_section.get("client_secret", "").strip()
    username = config_section.get("username", "").strip()
    password = config_section.get("password", "").strip()

    if refresh_token:
        credentials = dict(
            client_id=client_id,
            client_secret=None,
            refresh_token=refresh_token,
            redirect_uri=REDIRECT_URI,
            user_agent=user_agent,
        )
    elif all((client_id, client_secret, username, password, user_agent)):
        credentials = dict(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent,
        )
    else:
        return None

    try:
        reddit = _build_reddit(**credentials)
        # Trigger a lightweight request to validate session
        reddit.user.me()
        return reddit
    except Exception as exc:
        raise RedditAuthError(str(exc))


def post_to_reddit(reddit: praw.Reddit, subreddit: str, title: str, body: str) -> str:
    submission = reddit.subreddit(subreddit).submit(title=title, selftext=body)
    return submission.url


def fetch_submission_stats(reddit: praw.Reddit, url: str) -> tuple[int, int]:
    submission = reddit.submission(url=url)
    return submission.score, submission.num_comments
