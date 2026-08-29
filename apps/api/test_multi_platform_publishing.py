import asyncio
import os
import sys
import json
import uuid
import tempfile
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

sys.path.append(os.path.dirname(__file__))

from config import settings
from database import init_db, async_session_factory
from models.entities import Content, Asset, PlatformConnection, Publication, Job
from services.encryption_service import encryption_service
from services.publishing_service import publishing_service
from services.storage_service import storage_service
from connectors.instagram import instagram_connector, instagram_oauth
from connectors.linkedin import linkedin_connector, linkedin_oauth
from connectors.x_twitter import x_connector, x_oauth
from connectors.facebook import facebook_connector, facebook_oauth

class TestMultiPlatformPublishing(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await init_db()
        self.test_content_id = f"cnt_mp_{uuid.uuid4().hex[:8]}"
        self.test_conn_yt = f"conn_yt_{uuid.uuid4().hex[:6]}"
        self.test_conn_ig = f"conn_ig_{uuid.uuid4().hex[:6]}"
        self.test_conn_li = f"conn_li_{uuid.uuid4().hex[:6]}"
        self.test_conn_x = f"conn_x_{uuid.uuid4().hex[:6]}"
        self.test_conn_fb = f"conn_fb_{uuid.uuid4().hex[:6]}"
        self.test_video_path = os.path.join(tempfile.gettempdir(), f"reflow_mp_test_{uuid.uuid4().hex[:6]}.mp4")

        # Create small test video
        os.system(f"ffmpeg -y -f lavfi -i testsrc=duration=1:size=320x180:rate=30 -pix_fmt yuv420p {self.test_video_path} >/dev/null 2>&1")

    async def asyncTearDown(self):
        if os.path.exists(self.test_video_path):
            try: os.remove(self.test_video_path)
            except Exception: pass

        async with async_session_factory() as session:
            from sqlalchemy import delete
            await session.execute(delete(Publication).where(Publication.content_id == self.test_content_id))
            await session.execute(delete(PlatformConnection).where(PlatformConnection.id.in_([
                self.test_conn_yt, self.test_conn_ig, self.test_conn_li, self.test_conn_x, self.test_conn_fb
            ])))
            await session.execute(delete(Content).where(Content.id == self.test_content_id))
            await session.commit()

    async def test_01_instagram_reels_publishing(self):
        """Test 1: Verifies Instagram 3-stage Graph API container creation, polling, and publish."""
        # 1. Setup Content and Connection
        storage_key = f"content/{self.test_content_id}/assets/reel.mp4"
        with open(self.test_video_path, "rb") as f:
            await storage_service.put(storage_key, f.read())

        async with async_session_factory() as session:
            cnt = Content(id=self.test_content_id, title="IG Reel", content_type="VIDEO", status="READY")
            ast = Asset(id=f"ast_{uuid.uuid4().hex[:6]}", content_id=self.test_content_id, original_filename="reel.mp4", storage_key=storage_key, mime_type="video/mp4")
            conn = PlatformConnection(
                id=self.test_conn_ig,
                platform="instagram",
                name="Instagram Business",
                account_name="ReflowCreator",
                handle="@reflowcreator",
                status="CONNECTED",
                access_token_encrypted=encryption_service.encrypt_token("mock_ig_token")
            )
            session.add_all([cnt, ast, conn])
            await session.commit()

        pub_id = f"pub_ig_{uuid.uuid4().hex[:6]}"
        async with async_session_factory() as session:
            pub = Publication(
                id=pub_id,
                content_id=self.test_content_id,
                platform_connection_id=self.test_conn_ig,
                platform="instagram",
                status="QUEUED",
                title="Amazing Reel",
                description="Check this reel out #growth #viral",
                tags_json=json.dumps(["growth", "viral"]),
                request_payload_hash="hash_ig"
            )
            session.add(pub)
            await session.commit()

        # 2. Mock Graph API responses
        mock_container_resp = MagicMock()
        mock_container_resp.status_code = 200
        mock_container_resp.json.return_value = {"id": "ig_container_123"}

        mock_status_resp = MagicMock()
        mock_status_resp.status_code = 200
        mock_status_resp.json.return_value = {"status_code": "FINISHED"}

        mock_publish_resp = MagicMock()
        mock_publish_resp.status_code = 200
        mock_publish_resp.json.return_value = {"id": "ig_media_reel_999"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_post.side_effect = [mock_container_resp, mock_publish_resp]
            mock_get.return_value = mock_status_resp

            res = await publishing_service.execute_publication_job(pub_id)

            self.assertEqual(res["status"], "published")
            self.assertEqual(res["external_post_id"], "ig_media_reel_999")
            self.assertEqual(res["external_url"], "https://www.instagram.com/p/ig_media_reel_999")

        # Verify DB
        async with async_session_factory() as session:
            db_pub = await session.get(Publication, pub_id)
            self.assertEqual(db_pub.status, "PUBLISHED")
            self.assertEqual(db_pub.external_post_id, "ig_media_reel_999")

    async def test_02_linkedin_text_and_video_publishing(self):
        """Test 2: Verifies LinkedIn UGC Post creation."""
        async with async_session_factory() as session:
            cnt = Content(id=self.test_content_id, title="LinkedIn Thought Leadership", content_type="TEXT", status="READY")
            conn = PlatformConnection(
                id=self.test_conn_li,
                platform="linkedin",
                name="LinkedIn Profile",
                account_name="Jane Doe",
                handle="jane@example.com",
                status="CONNECTED",
                external_account_id="urn:li:person:abc12345",
                access_token_encrypted=encryption_service.encrypt_token("mock_li_token")
            )
            session.add_all([cnt, conn])
            await session.commit()

        pub_id = f"pub_li_{uuid.uuid4().hex[:6]}"
        async with async_session_factory() as session:
            pub = Publication(
                id=pub_id,
                content_id=self.test_content_id,
                platform_connection_id=self.test_conn_li,
                platform="linkedin",
                status="QUEUED",
                title="Content Repurposing Framework",
                description="Here is why automation saves 10 hours a week.",
                request_payload_hash="hash_li"
            )
            session.add(pub)
            await session.commit()

        mock_ugc_resp = MagicMock()
        mock_ugc_resp.status_code = 201
        mock_ugc_resp.json.return_value = {"id": "urn:li:share:55443322"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_ugc_resp

            res = await publishing_service.execute_publication_job(pub_id)
            self.assertEqual(res["status"], "published")
            self.assertEqual(res["external_post_id"], "urn:li:share:55443322")
            self.assertEqual(res["external_url"], "https://www.linkedin.com/feed/update/urn:li:share:55443322")

    async def test_03_x_twitter_tweet_publishing(self):
        """Test 3: Verifies X (Twitter) API v2 tweet publication and character limit validation."""
        async with async_session_factory() as session:
            cnt = Content(id=self.test_content_id, title="X Tweet", content_type="TEXT", status="READY")
            conn = PlatformConnection(
                id=self.test_conn_x,
                platform="x",
                name="X Account",
                account_name="CreatorX",
                handle="@creatorx",
                status="CONNECTED",
                access_token_encrypted=encryption_service.encrypt_token("mock_x_token")
            )
            session.add_all([cnt, conn])
            await session.commit()

        # Metadata validation test
        valid, err = x_connector.validate_metadata({"title": "Tweet", "description": "Short tweet."})
        self.assertTrue(valid)

        bad, err2 = x_connector.validate_metadata({"description": "A" * 300})
        self.assertFalse(bad)
        self.assertIn("exceeds 280 characters", err2)

        pub_id = f"pub_x_{uuid.uuid4().hex[:6]}"
        async with async_session_factory() as session:
            pub = Publication(
                id=pub_id,
                content_id=self.test_content_id,
                platform_connection_id=self.test_conn_x,
                platform="x",
                status="QUEUED",
                title="Tweet",
                description="Publishing to X via Reflow!",
                request_payload_hash="hash_x"
            )
            session.add(pub)
            await session.commit()

        mock_tweet_resp = MagicMock()
        mock_tweet_resp.status_code = 201
        mock_tweet_resp.json.return_value = {"data": {"id": "1829000111222", "text": "Publishing to X via Reflow!"}}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_tweet_resp

            res = await publishing_service.execute_publication_job(pub_id)
            self.assertEqual(res["status"], "published")
            self.assertEqual(res["external_post_id"], "1829000111222")
            self.assertEqual(res["external_url"], "https://x.com/i/status/1829000111222")

    async def test_04_facebook_page_publishing(self):
        """Test 4: Verifies Facebook Page feed post publication."""
        async with async_session_factory() as session:
            cnt = Content(id=self.test_content_id, title="FB Post", content_type="TEXT", status="READY")
            conn = PlatformConnection(
                id=self.test_conn_fb,
                platform="facebook",
                name="Facebook Page",
                account_name="Reflow Page",
                external_account_id="page_123456",
                status="CONNECTED",
                access_token_encrypted=encryption_service.encrypt_token("mock_fb_token")
            )
            session.add_all([cnt, conn])
            await session.commit()

        pub_id = f"pub_fb_{uuid.uuid4().hex[:6]}"
        async with async_session_factory() as session:
            pub = Publication(
                id=pub_id,
                content_id=self.test_content_id,
                platform_connection_id=self.test_conn_fb,
                platform="facebook",
                status="QUEUED",
                title="Facebook Post",
                description="Community update from Reflow.",
                request_payload_hash="hash_fb"
            )
            session.add(pub)
            await session.commit()

        mock_fb_resp = MagicMock()
        mock_fb_resp.status_code = 200
        mock_fb_resp.json.return_value = {"id": "page_123456_post_789"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_fb_resp

            res = await publishing_service.execute_publication_job(pub_id)
            self.assertEqual(res["status"], "published")
            self.assertEqual(res["external_post_id"], "page_123456_post_789")

    async def test_05_multi_platform_batch_publish_isolation(self):
        """
        Test 5: Verifies that in a batch multi-destination publish (YouTube + Instagram + LinkedIn),
        one platform's failure (e.g. Instagram rate limit) does NOT affect YouTube or LinkedIn success.
        """
        storage_key = f"content/{self.test_content_id}/assets/batch_video.mp4"
        with open(self.test_video_path, "rb") as f:
            await storage_service.put(storage_key, f.read())

        async with async_session_factory() as session:
            cnt = Content(id=self.test_content_id, title="Multi-Dest Video", content_type="VIDEO", status="READY")
            ast = Asset(id=f"ast_{uuid.uuid4().hex[:6]}", content_id=self.test_content_id, original_filename="batch_video.mp4", storage_key=storage_key, mime_type="video/mp4")
            
            conn_yt = PlatformConnection(id=self.test_conn_yt, platform="youtube", name="YouTube", status="CONNECTED", access_token_encrypted=encryption_service.encrypt_token("tok_yt"))
            conn_ig = PlatformConnection(id=self.test_conn_ig, platform="instagram", name="Instagram", status="CONNECTED", access_token_encrypted=encryption_service.encrypt_token("tok_ig"))
            conn_li = PlatformConnection(id=self.test_conn_li, platform="linkedin", name="LinkedIn", status="CONNECTED", access_token_encrypted=encryption_service.encrypt_token("tok_li"))
            
            session.add_all([cnt, ast, conn_yt, conn_ig, conn_li])
            await session.commit()

        # Create 3 independent publications
        pub_yt_id = f"pub_yt_{uuid.uuid4().hex[:6]}"
        pub_ig_id = f"pub_ig_{uuid.uuid4().hex[:6]}"
        pub_li_id = f"pub_li_{uuid.uuid4().hex[:6]}"

        async with async_session_factory() as session:
            p_yt = Publication(id=pub_yt_id, content_id=self.test_content_id, platform_connection_id=self.test_conn_yt, platform="youtube", status="QUEUED", title="Video on YT", request_payload_hash="h1")
            p_ig = Publication(id=pub_ig_id, content_id=self.test_content_id, platform_connection_id=self.test_conn_ig, platform="instagram", status="QUEUED", title="Video on IG", request_payload_hash="h2")
            p_li = Publication(id=pub_li_id, content_id=self.test_content_id, platform_connection_id=self.test_conn_li, platform="linkedin", status="QUEUED", title="Video on LI", request_payload_hash="h3")
            session.add_all([p_yt, p_ig, p_li])
            await session.commit()

        # Mock YouTube success
        mock_yt_init = MagicMock(status_code=200, headers={"Location": "https://upload.google.com/session"})
        mock_yt_up = MagicMock(status_code=200, json=lambda: {"id": "yt_multi_111", "snippet": {}, "status": {}})

        # Mock Instagram failure (e.g. 429 Rate limit)
        mock_ig_fail = MagicMock(status_code=429, text="Rate limit exceeded")

        # Mock LinkedIn success
        mock_li_reg = MagicMock(status_code=200, json=lambda: {"value": {"asset": "urn:li:asset:li_multi_222", "uploadMechanism": {"com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest": {"uploadUrl": "https://upload.linkedin.com"}}}})
        mock_li_put = MagicMock(status_code=200)
        mock_li_post = MagicMock(status_code=201, json=lambda: {"id": "urn:li:share:li_multi_222"})

        # 1. Execute YouTube Publication -> Must SUCCEED
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m_post, patch("httpx.AsyncClient.put", new_callable=AsyncMock) as m_put:
            m_post.return_value = mock_yt_init
            m_put.return_value = mock_yt_up
            res_yt = await publishing_service.execute_publication_job(pub_yt_id)
            self.assertEqual(res_yt["status"], "published")

        # 2. Execute Instagram Publication -> Must FAIL with RATE_LIMIT
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m_post:
            m_post.return_value = mock_ig_fail
            with self.assertRaises(ResourceWarning):
                await publishing_service.execute_publication_job(pub_ig_id)

        # 3. Execute LinkedIn Publication -> Must SUCCEED
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as m_post, patch("httpx.AsyncClient.put", new_callable=AsyncMock) as m_put:
            m_post.side_effect = [mock_li_reg, mock_li_post]
            m_put.return_value = mock_li_put
            res_li = await publishing_service.execute_publication_job(pub_li_id)
            self.assertEqual(res_li["status"], "published")

        # Verify Database States: YT=PUBLISHED, IG=FAILED (RATE_LIMIT), LI=PUBLISHED
        async with async_session_factory() as session:
            final_yt = await session.get(Publication, pub_yt_id)
            final_ig = await session.get(Publication, pub_ig_id)
            final_li = await session.get(Publication, pub_li_id)

            self.assertEqual(final_yt.status, "PUBLISHED")
            self.assertEqual(final_yt.external_post_id, "yt_multi_111")

            self.assertEqual(final_ig.status, "FAILED")
            self.assertEqual(final_ig.error_code, "RATE_LIMIT")

            self.assertEqual(final_li.status, "PUBLISHED")
            self.assertEqual(final_li.external_post_id, "urn:li:share:li_multi_222")

if __name__ == "__main__":
    unittest.main()
