import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
import httpx

from config import settings
from connectors.base import BasePlatformConnector, BaseOAuthProvider, PlatformCapabilities, not_implemented_response

class PinterestOAuthProvider(BaseOAuthProvider):
    platform_id = "pinterest"

    def get_authorization_url(self, state: str) -> str:
        return f"https://www.pinterest.com/oauth/?client_id={settings.PINTEREST_APP_ID or ''}&redirect_uri={settings.PINTEREST_REDIRECT_URI}&response_type=code&scope=boards:read,pins:read,pins:write&state={state}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        return not_implemented_response("pinterest", "oauth_exchange")

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        return not_implemented_response("pinterest", "token_refresh")

    async def revoke_token(self, token: str) -> bool:
        return True

    async def fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        return not_implemented_response("pinterest", "fetch_account")

class PinterestConnector(BasePlatformConnector):
    platform_id = "pinterest"
    platform_name = "Pinterest"

    def get_capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(
            video_upload=True,
            image_upload=True,
            carousel_upload=False,
            text_post=False,
            supported_aspect_ratios=["2:3", "9:16", "1:1"],
            max_description_length=500
        )

    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        desc = metadata.get("description") or ""
        if len(desc) > 500:
            return False, "Pinterest pin description exceeds 500 characters."
        return True, None

pinterest_oauth = PinterestOAuthProvider()
pinterest_connector = PinterestConnector()
