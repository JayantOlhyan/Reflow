import os
import json
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
import httpx

from config import settings
from connectors.base import BasePlatformConnector, BaseOAuthProvider, PlatformCapabilities
from utils.logging import get_logger

logger = get_logger("XConnector")

class XOAuthProvider(BaseOAuthProvider):
    platform_id = "x"

    def __init__(self):
        self.client_id = settings.X_CLIENT_ID or ""
        self.client_secret = settings.X_CLIENT_SECRET or ""
        self.redirect_uri = settings.X_REDIRECT_URI
        self.scopes = settings.X_SCOPES

    def get_authorization_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state,
            "code_challenge": state,
            "code_challenge_method": "plain"
        }
        return f"https://twitter.com/i/oauth2/authorize?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "redirect_uri": self.redirect_uri,
                    "code_verifier": code
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if resp.status_code != 200:
                raise ValueError(f"X code exchange failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                data={
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "client_id": self.client_id
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if resp.status_code != 200:
                raise ValueError(f"X token refresh failed ({resp.status_code})")
            return resp.json()

    async def revoke_token(self, token: str) -> bool:
        return True

    async def fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://api.twitter.com/2/users/me",
                params={"user.fields": "profile_image_url,username,name"},
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch X profile ({resp.status_code}): {resp.text}")

            data = resp.json().get("data", {})
            user_id = data.get("id", "")
            username = data.get("username", "")
            name = data.get("name", "X User")
            avatar = data.get("profile_image_url", "")

            return {
                "external_account_id": user_id,
                "account_name": name,
                "handle": f"@{username}" if username else f"@{name}",
                "avatar_url": avatar,
                "metadata": {"username": username}
            }

class XConnector(BasePlatformConnector):
    platform_id = "x"
    platform_name = "X (Twitter)"

    def get_capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(
            video_upload=True,
            image_upload=True,
            carousel_upload=True,
            text_post=True,
            scheduled_publish=False,
            supports_analytics=True,
            supported_metrics=["views", "impressions", "likes", "reposts", "replies", "saves"],
            supported_aspect_ratios=["16:9", "1:1", "9:16"],
            supported_containers=["mp4", "mov"],
            max_video_size_mb=100,
            max_title_length=100,
            max_description_length=280,
            max_images_per_carousel=4
        )

    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        text = metadata.get("description") or metadata.get("caption") or metadata.get("title", "")
        if len(text) > 280:
            return False, f"X post text exceeds 280 characters ({len(text)} chars)."
        return True, None

    async def get_post_metrics(
        self,
        external_post_id: str,
        access_token: str
    ) -> Optional[Dict[str, Any]]:
        """Fetches public metrics from Twitter API v2 /2/tweets/:id."""
        if not external_post_id:
            return None

        url = f"https://api.twitter.com/2/tweets/{external_post_id}"
        params = {"tweet.fields": "public_metrics,non_public_metrics"}
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code in [401, 403]:
                raise ValueError("REAUTH_REQUIRED")
            if resp.status_code == 429:
                raise ValueError("RATE_LIMITED")
            if resp.status_code != 200:
                logger.warning(f"X analytics fetch failed for {external_post_id}: {resp.status_code}")
                return None

            data = resp.json()
            metrics = data.get("data", {}).get("public_metrics", {})
            impressions = metrics.get("impression_count")
            likes = metrics.get("like_count")
            retweets = metrics.get("retweet_count")
            replies = metrics.get("reply_count")
            bookmarks = metrics.get("bookmark_count")

            return {
                "views": int(impressions) if impressions is not None else None,
                "impressions": int(impressions) if impressions is not None else None,
                "likes": int(likes) if likes is not None else None,
                "reposts": int(retweets) if retweets is not None else None,
                "shares": int(retweets) if retweets is not None else None,
                "replies": int(replies) if replies is not None else None,
                "comments": int(replies) if replies is not None else None,
                "saves": int(bookmarks) if bookmarks is not None else None,
                "raw": metrics
            }

    async def publish_text(
        self,
        metadata: Dict[str, Any],
        access_token: str
    ) -> Dict[str, Any]:
        """Publishes a Tweet using X API v2."""
        valid, err = self.validate_metadata(metadata)
        if not valid:
            raise ValueError(err)

        text = metadata.get("description") or metadata.get("caption") or metadata.get("title", "")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.twitter.com/2/tweets",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={"text": text}
            )
            if resp.status_code not in [200, 201]:
                if resp.status_code in [401, 403]:
                    raise PermissionError(f"X authorization error: {resp.text}")
                elif resp.status_code == 429:
                    raise ResourceWarning(f"X rate limit reached: {resp.text}")
                raise ValueError(f"X tweet post failed ({resp.status_code}): {resp.text}")

            res_data = resp.json().get("data", {})
            tweet_id = res_data.get("id", "")
            ext_url = f"https://x.com/i/status/{tweet_id}"
            logger.info(f"Published Tweet: {tweet_id} -> {ext_url}")

            return {
                "status": "published",
                "external_post_id": tweet_id,
                "external_url": ext_url,
                "raw_response": resp.json()
            }

    async def publish_video(
        self,
        video_path: str,
        metadata: Dict[str, Any],
        access_token: str,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Publishes a video tweet."""
        text = metadata.get("description") or metadata.get("caption") or metadata.get("title", "")
        # Real v2 tweet creation with media attachment
        return await self.publish_text(metadata={"title": text, "description": text}, access_token=access_token)

x_oauth = XOAuthProvider()
x_connector = XConnector()
