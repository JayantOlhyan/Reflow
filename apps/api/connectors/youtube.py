import os
import json
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
import httpx

from config import settings
from connectors.base import BasePlatformConnector, BaseOAuthProvider, PlatformCapabilities
from utils.logging import get_logger

logger = get_logger("YouTubeConnector")

class YouTubeOAuthProvider(BaseOAuthProvider):
    platform_id = "youtube"

    def __init__(self):
        self.client_id = settings.YOUTUBE_CLIENT_ID or ""
        self.client_secret = settings.YOUTUBE_CLIENT_SECRET or ""
        self.redirect_uri = settings.YOUTUBE_REDIRECT_URI
        self.scopes = settings.YOUTUBE_SCOPES

    def get_authorization_url(self, state: str) -> str:
        """Constructs Google OAuth 2.0 consent authorization URL."""
        if not self.client_id:
            logger.warning("YOUTUBE_CLIENT_ID is not configured in environment.")

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchanges authorization code for access and refresh tokens."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            if resp.status_code != 200:
                logger.error(f"YouTube OAuth code exchange failed: {resp.status_code} {resp.text}")
                raise ValueError(f"OAuth code exchange failed: {resp.status_code}")
            return resp.json()

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refreshes an expired access token using the stored refresh token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            )
            if resp.status_code != 200:
                logger.error(f"YouTube OAuth token refresh failed: {resp.status_code}")
                raise ValueError(f"OAuth token refresh failed: {resp.status_code}")
            return resp.json()

    async def revoke_token(self, token: str) -> bool:
        """Revokes token access on Google's authorization server."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"https://oauth2.googleapis.com/revoke?token={urllib.parse.quote(token)}"
                )
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"YouTube revoke token encountered non-fatal error: {e}")
            return False

    async def fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        """Retrieves YouTube channel identity (name, handle, ID, and avatar)."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "snippet", "mine": "true"},
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if resp.status_code != 200:
                logger.error(f"Failed to fetch YouTube channel info: {resp.status_code} {resp.text}")
                raise ValueError(f"Channel profile lookup failed: {resp.status_code}")

            data = resp.json()
            items = data.get("items", [])
            if not items:
                raise ValueError("No YouTube channel found for authenticated Google account.")

            channel = items[0]
            snippet = channel.get("snippet", {})
            channel_id = channel.get("id", "")
            title = snippet.get("title", "YouTube Channel")
            custom_url = snippet.get("customUrl", f"@{title.replace(' ', '')}")
            avatar = snippet.get("thumbnails", {}).get("default", {}).get("url", "")

            return {
                "external_account_id": channel_id,
                "account_name": title,
                "handle": custom_url,
                "avatar_url": avatar,
                "metadata": {
                    "description": snippet.get("description", ""),
                    "published_at": snippet.get("publishedAt", "")
                }
            }

class YouTubeConnector(BasePlatformConnector):
    platform_id = "youtube"
    platform_name = "YouTube"

    def get_capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(
            video_upload=True,
            image_upload=False,
            carousel_upload=False,
            text_post=False,
            scheduled_publish=True,
            supported_aspect_ratios=["16:9", "9:16", "1:1", "4:5"],
            supported_containers=["mp4", "mov", "webm"],
            max_video_size_mb=500,
            max_title_length=100,
            max_description_length=5000
        )

    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        title = metadata.get("title", "").strip()
        if not title:
            return False, "Title is required for YouTube video publication."
        if len(title) > 100:
            return False, f"YouTube title exceeds 100 characters ({len(title)} chars)."

        desc = metadata.get("description", "")
        if len(desc) > 5000:
            return False, f"YouTube description exceeds 5000 characters ({len(desc)} chars)."

        privacy = metadata.get("privacy", "PRIVATE").upper()
        if privacy not in ["PRIVATE", "UNLISTED", "PUBLIC"]:
            return False, f"Invalid privacy status '{privacy}'. Must be PRIVATE, UNLISTED, or PUBLIC."

        return True, None

    async def publish_video(
        self,
        video_path: str,
        metadata: Dict[str, Any],
        access_token: str,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Executes a real resumable video upload to YouTube Data API v3.
        """
        # 1. Pre-validation
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file missing at path: {video_path}")

        file_size = os.path.getsize(video_path)
        if file_size == 0:
            raise ValueError("Video file size is 0 bytes.")

        valid, error_msg = self.validate_metadata(metadata)
        if not valid:
            raise ValueError(f"Metadata validation error: {error_msg}")

        title = metadata.get("title", "Reflow Video").strip()
        description = metadata.get("description", "").strip()
        tags = metadata.get("tags", [])
        privacy = metadata.get("privacy", "PRIVATE").lower()

        # 2. Resumable Upload Initiation
        init_body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22" # People & Blogs default
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False
            }
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Step A: Initiate session
            init_resp = await client.post(
                "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Type": "video/mp4",
                    "X-Upload-Content-Length": str(file_size)
                },
                json=init_body
            )

            if init_resp.status_code not in [200, 201]:
                if init_resp.status_code in [401, 403]:
                    raise PermissionError(f"YouTube authentication failed ({init_resp.status_code}): {init_resp.text}")
                elif init_resp.status_code == 429:
                    raise ResourceWarning(f"YouTube rate limit reached (429): {init_resp.text}")
                raise ValueError(f"YouTube upload initialization failed ({init_resp.status_code}): {init_resp.text}")

            upload_url = init_resp.headers.get("Location")
            if not upload_url:
                raise ValueError("YouTube API did not return a resumable upload Location URL.")

            # Step B: Upload file binary stream
            with open(video_path, "rb") as video_file:
                upload_resp = await client.put(
                    upload_url,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Length": str(file_size)
                    },
                    content=video_file.read()
                )

            if upload_resp.status_code not in [200, 201]:
                logger.error(f"YouTube video upload failed: {upload_resp.status_code} {upload_resp.text}")
                raise ValueError(f"YouTube upload failed ({upload_resp.status_code}): {upload_resp.text}")

            res_json = upload_resp.json()
            video_id = res_json.get("id")
            if not video_id:
                raise ValueError("YouTube API response did not contain a valid video ID.")

            external_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"Successfully published YouTube video: {video_id} -> {external_url}")

            return {
                "status": "published",
                "external_post_id": video_id,
                "external_url": external_url,
                "published_at": res_json.get("snippet", {}).get("publishedAt"),
                "raw_response": res_json
            }

youtube_oauth = YouTubeOAuthProvider()
youtube_connector = YouTubeConnector()
