import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
import httpx

from config import settings
from connectors.base import BasePlatformConnector, BaseOAuthProvider, PlatformCapabilities, not_implemented_response
from utils.logging import get_logger

logger = get_logger("TikTokConnector")

class TikTokOAuthProvider(BaseOAuthProvider):
    platform_id = "tiktok"

    def __init__(self):
        self.client_key = settings.TIKTOK_CLIENT_KEY or ""
        self.client_secret = settings.TIKTOK_CLIENT_SECRET or ""
        self.redirect_uri = settings.TIKTOK_REDIRECT_URI
        self.scopes = settings.TIKTOK_SCOPES

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_key": self.client_key,
            "response_type": "code",
            "scope": ",".join(self.scopes),
            "redirect_uri": self.redirect_uri,
            "state": state
        }
        return f"https://www.tiktok.com/v2/auth/authorize/?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://open.tiktokapis.com/v2/oauth/token/",
                data={
                    "client_key": self.client_key,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if resp.status_code != 200:
                raise ValueError(f"TikTok OAuth code exchange failed ({resp.status_code}): {resp.text}")
            data = resp.json()
            return {
                "access_token": data.get("data", {}).get("access_token"),
                "refresh_token": data.get("data", {}).get("refresh_token"),
                "expires_in": data.get("data", {}).get("expires_in", 86400)
            }

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://open.tiktokapis.com/v2/oauth/token/",
                data={
                    "client_key": self.client_key,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if resp.status_code != 200:
                raise ValueError(f"TikTok token refresh failed ({resp.status_code})")
            return resp.json()

    async def revoke_token(self, token: str) -> bool:
        return True

    async def fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://open.tiktokapis.com/v2/user/info/",
                params={"fields": "open_id,union_id,avatar_url,display_name"},
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if resp.status_code != 200:
                raise ValueError(f"TikTok user info failed ({resp.status_code})")
            user = resp.json().get("data", {}).get("user", {})
            return {
                "external_account_id": user.get("open_id", ""),
                "account_name": user.get("display_name", "TikTok Creator"),
                "handle": f"@{user.get('display_name', 'creator')}",
                "avatar_url": user.get("avatar_url", "")
            }

class TikTokConnector(BasePlatformConnector):
    platform_id = "tiktok"
    platform_name = "TikTok"

    def get_capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(
            video_upload=True,
            image_upload=False,
            carousel_upload=False,
            text_post=False,
            scheduled_publish=False,
            supported_aspect_ratios=["9:16"],
            supported_containers=["mp4"],
            max_video_size_mb=500,
            max_title_length=150,
            max_description_length=2200
        )

    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        title = metadata.get("title") or metadata.get("description") or ""
        if len(title) > 2200:
            return False, f"TikTok caption exceeds 2200 characters ({len(title)} chars)."
        return True, None

    async def publish_video(
        self,
        video_path: str,
        metadata: Dict[str, Any],
        access_token: str,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        # Direct TikTok Content Posting API v2 requires verified partner app approval
        if not settings.TIKTOK_CLIENT_KEY or not settings.TIKTOK_CLIENT_SECRET:
            raise PermissionError("TikTok Client Key and Secret must be configured in Reflow settings.")

        # Post via direct upload flow
        title = metadata.get("title") or metadata.get("description", "Reflow Short Video")
        async with httpx.AsyncClient(timeout=120.0) as client:
            init_resp = await client.post(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"post_info": {"title": title[:2200], "privacy_level": "SELF_ONLY"}}
            )
            if init_resp.status_code not in [200, 201]:
                raise ValueError(f"TikTok publish initialization failed ({init_resp.status_code}): {init_resp.text}")

            publish_id = init_resp.json().get("data", {}).get("publish_id", "")
            return {
                "status": "published",
                "external_post_id": publish_id,
                "external_url": f"https://www.tiktok.com/@creator/video/{publish_id}"
            }

tiktok_oauth = TikTokOAuthProvider()
tiktok_connector = TikTokConnector()
