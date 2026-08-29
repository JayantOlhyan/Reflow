import os
import json
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
import httpx

from config import settings
from connectors.base import BasePlatformConnector, BaseOAuthProvider, PlatformCapabilities
from utils.logging import get_logger

logger = get_logger("FacebookConnector")

class FacebookOAuthProvider(BaseOAuthProvider):
    platform_id = "facebook"

    def __init__(self):
        self.client_id = settings.META_CLIENT_ID or ""
        self.client_secret = settings.META_CLIENT_SECRET or ""
        self.redirect_uri = settings.FACEBOOK_REDIRECT_URI
        self.scopes = settings.FACEBOOK_SCOPES

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": ",".join(self.scopes),
            "state": state
        }
        return f"https://www.facebook.com/v19.0/dialog/oauth?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://graph.facebook.com/v19.0/oauth/access_token",
                params={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "code": code
                }
            )
            if resp.status_code != 200:
                raise ValueError(f"Facebook OAuth exchange failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://graph.facebook.com/v19.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "fb_exchange_token": refresh_token
                }
            )
            if resp.status_code != 200:
                raise ValueError(f"Facebook token refresh failed: {resp.status_code}")
            return resp.json()

    async def revoke_token(self, token: str) -> bool:
        return True

    async def fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        """Fetches Facebook Page identity for posting."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://graph.facebook.com/v19.0/me/accounts",
                params={"fields": "id,name,picture", "access_token": access_token}
            )
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch Facebook Pages: {resp.status_code}")

            data = resp.json().get("data", [])
            if not data:
                raise ValueError("No manageable Facebook Page found for this Meta account.")

            page = data[0]
            page_id = page.get("id", "")
            name = page.get("name", "Facebook Page")
            avatar = page.get("picture", {}).get("data", {}).get("url", "")

            return {
                "external_account_id": page_id,
                "account_name": name,
                "handle": f"Page: {name}",
                "avatar_url": avatar,
                "metadata": {"page_id": page_id}
            }

class FacebookConnector(BasePlatformConnector):
    platform_id = "facebook"
    platform_name = "Facebook"

    def get_capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(
            video_upload=True,
            image_upload=True,
            carousel_upload=False,
            text_post=True,
            scheduled_publish=True,
            supports_analytics=True,
            supported_metrics=["views", "impressions", "likes", "comments", "shares"],
            supported_aspect_ratios=["16:9", "1:1", "4:5", "9:16"],
            supported_containers=["mp4", "mov"],
            max_video_size_mb=500,
            max_title_length=100,
            max_description_length=5000
        )

    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        msg = metadata.get("description") or metadata.get("caption") or metadata.get("title", "")
        if len(msg) > 5000:
            return False, f"Facebook message exceeds 5000 characters ({len(msg)} chars)."
        return True, None

    async def get_post_metrics(
        self,
        external_post_id: str,
        access_token: str
    ) -> Optional[Dict[str, Any]]:
        """Fetches post reactions/comments from Facebook Graph API."""
        if not external_post_id:
            return None

        url = f"https://graph.facebook.com/v19.0/{external_post_id}"
        params = {
            "fields": "reactions.summary(total_count),comments.summary(total_count),shares",
            "access_token": access_token
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code in [401, 403]:
                raise ValueError("REAUTH_REQUIRED")
            if resp.status_code == 429:
                raise ValueError("RATE_LIMITED")
            if resp.status_code != 200:
                logger.warning(f"Facebook analytics fetch failed for {external_post_id}: {resp.status_code}")
                return None

            data = resp.json()
            reactions = data.get("reactions", {}).get("summary", {}).get("total_count")
            comments = data.get("comments", {}).get("summary", {}).get("total_count")
            shares = data.get("shares", {}).get("count")

            return {
                "likes": int(reactions) if reactions is not None else None,
                "comments": int(comments) if comments is not None else None,
                "shares": int(shares) if shares is not None else None,
                "raw": data
            }

    async def publish_text(
        self,
        metadata: Dict[str, Any],
        access_token: str
    ) -> Dict[str, Any]:
        """Publishes a text status to Facebook Page feed."""
        valid, err = self.validate_metadata(metadata)
        if not valid:
            raise ValueError(err)

        message = metadata.get("description") or metadata.get("caption") or metadata.get("title", "")
        page_id = metadata.get("external_account_id") or "me"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://graph.facebook.com/v19.0/{page_id}/feed",
                data={"message": message, "access_token": access_token}
            )
            if resp.status_code not in [200, 201]:
                if resp.status_code in [401, 403]:
                    raise PermissionError(f"Facebook permission error: {resp.text}")
                raise ValueError(f"Facebook post failed: {resp.text}")

            post_id = resp.json().get("id", "")
            ext_url = f"https://www.facebook.com/{post_id}"
            return {
                "status": "published",
                "external_post_id": post_id,
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
        """Publishes a video to Facebook Page."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file missing: {video_path}")

        title = metadata.get("title", "Reflow Video")
        desc = metadata.get("description") or metadata.get("caption", "")
        page_id = metadata.get("external_account_id") or "me"

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"https://graph-video.facebook.com/v19.0/{page_id}/videos",
                data={"title": title, "description": desc, "access_token": access_token}
            )
            if resp.status_code not in [200, 201]:
                raise ValueError(f"Facebook video upload failed: {resp.text}")

            video_id = resp.json().get("id", "")
            ext_url = f"https://www.facebook.com/{page_id}/videos/{video_id}"
            return {
                "status": "published",
                "external_post_id": video_id,
                "external_url": ext_url,
                "raw_response": resp.json()
            }

facebook_oauth = FacebookOAuthProvider()
facebook_connector = FacebookConnector()
