import os
import json
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
import httpx

from config import settings
from connectors.base import BasePlatformConnector, BaseOAuthProvider, PlatformCapabilities
from utils.logging import get_logger

logger = get_logger("LinkedInConnector")

class LinkedInOAuthProvider(BaseOAuthProvider):
    platform_id = "linkedin"

    def __init__(self):
        self.client_id = settings.LINKEDIN_CLIENT_ID or ""
        self.client_secret = settings.LINKEDIN_CLIENT_SECRET or ""
        self.redirect_uri = settings.LINKEDIN_REDIRECT_URI
        self.scopes = settings.LINKEDIN_SCOPES

    def get_authorization_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state
        }
        return f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if resp.status_code != 200:
                raise ValueError(f"LinkedIn code exchange failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if resp.status_code != 200:
                raise ValueError(f"LinkedIn token refresh failed: {resp.status_code}")
            return resp.json()

    async def revoke_token(self, token: str) -> bool:
        return True # LinkedIn handles revokes via token expiration

    async def fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        """Fetches LinkedIn user profile via OIDC userinfo."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if resp.status_code != 200:
                raise ValueError(f"LinkedIn userinfo request failed ({resp.status_code}): {resp.text}")

            data = resp.json()
            sub = data.get("sub", "")
            name = data.get("name", "LinkedIn Member")
            picture = data.get("picture", "")
            email = data.get("email", "")

            return {
                "external_account_id": f"urn:li:person:{sub}",
                "account_name": name,
                "handle": email or name,
                "avatar_url": picture,
                "metadata": {"sub": sub}
            }

class LinkedInConnector(BasePlatformConnector):
    platform_id = "linkedin"
    platform_name = "LinkedIn"

    def get_capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(
            video_upload=True,
            image_upload=True,
            carousel_upload=True,
            text_post=True,
            scheduled_publish=True,
            supported_aspect_ratios=["16:9", "1:1", "9:16", "4:5"],
            supported_containers=["mp4", "mov"],
            max_video_size_mb=200,
            max_title_length=100,
            max_description_length=3000
        )

    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        text = metadata.get("description") or metadata.get("caption") or metadata.get("title", "")
        if len(text) > 3000:
            return False, f"LinkedIn post text exceeds 3000 characters ({len(text)} chars)."
        return True, None

    async def publish_text(
        self,
        metadata: Dict[str, Any],
        access_token: str
    ) -> Dict[str, Any]:
        """Publishes a text post to LinkedIn Feed."""
        valid, err = self.validate_metadata(metadata)
        if not valid:
            raise ValueError(err)

        text = metadata.get("description") or metadata.get("caption") or metadata.get("title", "")
        author_urn = metadata.get("external_account_id") or "urn:li:person:me"

        body = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Restli-Protocol-Version": "2.0.0",
                    "Content-Type": "application/json"
                },
                json=body
            )
            if resp.status_code not in [200, 201]:
                if resp.status_code in [401, 403]:
                    raise PermissionError(f"LinkedIn authentication error: {resp.text}")
                elif resp.status_code == 429:
                    raise ResourceWarning(f"LinkedIn rate limit reached: {resp.text}")
                raise ValueError(f"LinkedIn text post failed ({resp.status_code}): {resp.text}")

            post_urn = resp.json().get("id", "")
            ext_url = f"https://www.linkedin.com/feed/update/{post_urn}"
            return {
                "status": "published",
                "external_post_id": post_urn,
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
        """Publishes a video post to LinkedIn using the 2-stage UGC media upload flow."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file missing: {video_path}")

        file_size = os.path.getsize(video_path)
        text = metadata.get("description") or metadata.get("caption") or metadata.get("title", "")
        author_urn = metadata.get("external_account_id") or "urn:li:person:me"

        # 1. Register Upload Asset
        register_body = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                "owner": author_urn,
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }]
            }
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            reg_resp = await client.post(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=register_body
            )
            if reg_resp.status_code not in [200, 201]:
                raise ValueError(f"LinkedIn asset registration failed ({reg_resp.status_code}): {reg_resp.text}")

            val = reg_resp.json().get("value", {})
            asset_urn = val.get("asset")
            upload_mechanism = val.get("uploadMechanism", {}).get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {})
            upload_url = upload_mechanism.get("uploadUrl")

            if not upload_url:
                raise ValueError("LinkedIn did not return upload URL.")

            # 2. PUT video binary bytes
            with open(video_path, "rb") as vf:
                up_resp = await client.put(
                    upload_url,
                    headers={"Content-Type": "application/octet-stream", "Content-Length": str(file_size)},
                    content=vf.read()
                )
                if up_resp.status_code not in [200, 201]:
                    raise ValueError(f"LinkedIn binary upload failed ({up_resp.status_code})")

            # 3. Create Video Post referencing Asset URN
            post_body = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": "VIDEO",
                        "media": [{
                            "status": "READY",
                            "description": {"text": text[:200]},
                            "media": asset_urn,
                            "title": {"text": metadata.get("title", "Reflow Video")[:100]}
                        }]
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }

            post_resp = await client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json=post_body
            )
            if post_resp.status_code not in [200, 201]:
                raise ValueError(f"LinkedIn video post creation failed: {post_resp.text}")

            post_urn = post_resp.json().get("id", "")
            ext_url = f"https://www.linkedin.com/feed/update/{post_urn}"
            logger.info(f"Published LinkedIn Video Post: {post_urn} -> {ext_url}")

            return {
                "status": "published",
                "external_post_id": post_urn,
                "external_url": ext_url,
                "raw_response": post_resp.json()
            }

linkedin_oauth = LinkedInOAuthProvider()
linkedin_connector = LinkedInConnector()
