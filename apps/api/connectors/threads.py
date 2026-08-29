import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
import httpx

from config import settings
from connectors.base import BasePlatformConnector, BaseOAuthProvider, PlatformCapabilities, not_implemented_response

class ThreadsOAuthProvider(BaseOAuthProvider):
    platform_id = "threads"

    def get_authorization_url(self, state: str) -> str:
        return f"https://threads.net/oauth/authorize?client_id={settings.THREADS_APP_ID or ''}&redirect_uri={settings.THREADS_REDIRECT_URI}&scope=threads_basic,threads_content_publish&response_type=code&state={state}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        return not_implemented_response("threads", "oauth_exchange")

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        return not_implemented_response("threads", "token_refresh")

    async def revoke_token(self, token: str) -> bool:
        return True

    async def fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        return not_implemented_response("threads", "fetch_account")

class ThreadsConnector(BasePlatformConnector):
    platform_id = "threads"
    platform_name = "Threads"

    def get_capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(
            video_upload=True,
            image_upload=True,
            carousel_upload=True,
            text_post=True,
            supported_aspect_ratios=["1:1", "9:16", "16:9"],
            max_description_length=500
        )

    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        desc = metadata.get("description") or metadata.get("caption") or ""
        if len(desc) > 500:
            return False, "Threads post text exceeds 500 characters."
        return True, None

threads_oauth = ThreadsOAuthProvider()
threads_connector = ThreadsConnector()
