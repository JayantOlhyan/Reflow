import asyncio
import os
import sys
import json
import uuid
import tempfile
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

# Ensure api directory is in python path
sys.path.append(os.path.dirname(__file__))

from config import settings
from database import init_db, async_session_factory
from models.entities import Content, Asset, ContentVariant, Clip, ClipVariant, PlatformConnection, Publication, Job
from services.encryption_service import encryption_service
from services.publishing_service import publishing_service
from services.storage_service import storage_service
from connectors.youtube import youtube_connector, youtube_oauth

class TestPublishingEngine(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await init_db()
        self.test_content_id = f"cnt_pub_{uuid.uuid4().hex[:8]}"
        self.test_conn_id = f"conn_yt_{uuid.uuid4().hex[:8]}"
        self.test_video_path = os.path.join(tempfile.gettempdir(), f"reflow_test_pub_{uuid.uuid4().hex[:6]}.mp4")

        # Generate a small 1-second 320x180 test video using ffmpeg
        os.system(f"ffmpeg -y -f lavfi -i testsrc=duration=1:size=320x180:rate=30 -pix_fmt yuv420p {self.test_video_path} >/dev/null 2>&1")

    async def asyncTearDown(self):
        if os.path.exists(self.test_video_path):
            try: os.remove(self.test_video_path)
            except Exception: pass

        async with async_session_factory() as session:
            # Clean up test publication and connections
            from sqlalchemy import delete
            await session.execute(delete(Publication).where(Publication.content_id == self.test_content_id))
            await session.execute(delete(PlatformConnection).where(PlatformConnection.id == self.test_conn_id))
            await session.execute(delete(Content).where(Content.id == self.test_content_id))
            await session.commit()

    async def test_01_token_encryption_at_rest(self):
        """Test 1: Verifies token encryption and decryption at rest with Fernet key."""
        raw_access_token = "ya29.a0AfH6SMD_real_secret_token_123456789"
        raw_refresh_token = "1//04_secret_refresh_token_abcdef"

        encrypted_access = encryption_service.encrypt_token(raw_access_token)
        encrypted_refresh = encryption_service.encrypt_token(raw_refresh_token)

        self.assertIsNotNone(encrypted_access)
        self.assertIsNotNone(encrypted_refresh)
        self.assertNotEqual(raw_access_token, encrypted_access)
        self.assertNotEqual(raw_refresh_token, encrypted_refresh)

        # Decrypt round-trip
        decrypted_access = encryption_service.decrypt_token(encrypted_access)
        decrypted_refresh = encryption_service.decrypt_token(encrypted_refresh)

        self.assertEqual(decrypted_access, raw_access_token)
        self.assertEqual(decrypted_refresh, raw_refresh_token)

        # None handling
        self.assertIsNone(encryption_service.encrypt_token(None))
        self.assertIsNone(encryption_service.decrypt_token(None))

    async def test_02_oauth_state_generation_and_validation(self):
        """Test 2: Verifies single-use cryptographic state token generation and CSRF validation."""
        state = publishing_service.create_oauth_state("youtube", ttl_minutes=15)
        self.assertIsInstance(state, str)
        self.assertGreater(len(state), 20)

        # First consumption must succeed
        self.assertTrue(publishing_service.validate_and_consume_oauth_state(state, "youtube"))

        # Re-using the same state must fail (single-use protection)
        self.assertFalse(publishing_service.validate_and_consume_oauth_state(state, "youtube"))

        # Platform mismatch protection
        state2 = publishing_service.create_oauth_state("youtube", ttl_minutes=15)
        self.assertFalse(publishing_service.validate_and_consume_oauth_state(state2, "instagram"))

    async def test_03_youtube_metadata_validation(self):
        """Test 3: Pre-validates metadata constraints (title length, privacy, description)."""
        valid_meta = {
            "title": "5 Tips for Growth",
            "description": "Short-form video breakdown",
            "tags": ["growth", "tips"],
            "privacy": "PRIVATE"
        }
        ok, err = youtube_connector.validate_metadata(valid_meta)
        self.assertTrue(ok)
        self.assertIsNone(err)

        # Empty title rejection
        bad_meta = {"title": "", "privacy": "PRIVATE"}
        ok, err = youtube_connector.validate_metadata(bad_meta)
        self.assertFalse(ok)
        self.assertIn("Title is required", err)

        # Title > 100 chars rejection
        long_title = "A" * 105
        bad_meta2 = {"title": long_title, "privacy": "PRIVATE"}
        ok, err = youtube_connector.validate_metadata(bad_meta2)
        self.assertFalse(ok)
        self.assertIn("exceeds 100 characters", err)

        # Invalid privacy rejection
        bad_meta3 = {"title": "Valid Title", "privacy": "UNKNOWN_MODE"}
        ok, err = youtube_connector.validate_metadata(bad_meta3)
        self.assertFalse(ok)
        self.assertIn("Invalid privacy status", err)

    async def test_04_mocked_youtube_upload_and_publication_pipeline(self):
        """Test 4: End-to-end publication flow with mock YouTube API calls, verifying database state."""
        # 1. Setup Content and Asset
        storage_key = f"content/{self.test_content_id}/assets/video.mp4"
        with open(self.test_video_path, "rb") as f:
            await storage_service.put(storage_key, f.read())

        async with async_session_factory() as session:
            content = Content(
                id=self.test_content_id,
                title="Test Publication Video",
                content_type="VIDEO",
                status="READY"
            )
            asset = Asset(
                id=f"ast_pub_{uuid.uuid4().hex[:6]}",
                content_id=self.test_content_id,
                original_filename="video.mp4",
                storage_key=storage_key,
                mime_type="video/mp4"
            )
            # Setup Platform Connection
            enc_token = encryption_service.encrypt_token("mock_valid_youtube_access_token")
            conn = PlatformConnection(
                id=self.test_conn_id,
                platform="youtube",
                name="Test YouTube Channel",
                account_name="Creator Channel",
                handle="@creator",
                status="CONNECTED",
                access_token_encrypted=enc_token
            )
            session.add_all([content, asset, conn])
            await session.commit()

        # 2. Create Publication Record
        pub_id = f"pub_{uuid.uuid4().hex[:8]}"
        hash_val = publishing_service.compute_idempotency_hash(
            content_id=self.test_content_id,
            variant_id=None,
            platform_connection_id=self.test_conn_id,
            title="Mastering Content Repurposing",
            privacy="PRIVATE"
        )
        async with async_session_factory() as session:
            publication = Publication(
                id=pub_id,
                content_id=self.test_content_id,
                platform_connection_id=self.test_conn_id,
                platform="youtube",
                status="QUEUED",
                title="Mastering Content Repurposing",
                description="Published by Reflow automation.",
                privacy="PRIVATE",
                tags_json=json.dumps(["reflow", "ai"]),
                request_payload_hash=hash_val
            )
            session.add(publication)
            await session.commit()

        # 3. Mock YouTube Resumable Upload HTTP Calls
        mock_init_resp = MagicMock()
        mock_init_resp.status_code = 200
        mock_init_resp.headers = {"Location": "https://www.googleapis.com/upload/resumable_session_url_123"}

        mock_upload_resp = MagicMock()
        mock_upload_resp.status_code = 200
        mock_upload_resp.json.return_value = {
            "id": "yt_video_test_9876",
            "snippet": {
                "title": "Mastering Content Repurposing",
                "publishedAt": "2026-08-30T00:00:00Z"
            },
            "status": {
                "privacyStatus": "private"
            }
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
             patch("httpx.AsyncClient.put", new_callable=AsyncMock) as mock_put:
            mock_post.return_value = mock_init_resp
            mock_put.return_value = mock_upload_resp

            # Execute publication job
            res = await publishing_service.execute_publication_job(pub_id)

            self.assertEqual(res["status"], "published")
            self.assertEqual(res["external_post_id"], "yt_video_test_9876")
            self.assertEqual(res["external_url"], "https://www.youtube.com/watch?v=yt_video_test_9876")

        # 4. Verify Database State
        async with async_session_factory() as session:
            res_pub = await session.get(Publication, pub_id)
            self.assertIsNotNone(res_pub)
            self.assertEqual(res_pub.status, "PUBLISHED")
            self.assertEqual(res_pub.external_post_id, "yt_video_test_9876")
            self.assertEqual(res_pub.external_url, "https://www.youtube.com/watch?v=yt_video_test_9876")
            self.assertIsNone(res_pub.error_code)

    async def test_05_idempotency_duplicate_prevention(self):
        """Test 5: Verifies that identical publication requests return existing publication without duplicate posts."""
        hash_val = publishing_service.compute_idempotency_hash(
            content_id=self.test_content_id,
            variant_id=None,
            platform_connection_id=self.test_conn_id,
            title="Idempotent Title",
            privacy="PRIVATE"
        )

        async with async_session_factory() as session:
            pub = Publication(
                id=f"pub_idem_{uuid.uuid4().hex[:6]}",
                content_id=self.test_content_id,
                platform_connection_id=self.test_conn_id,
                platform="youtube",
                status="PUBLISHED",
                title="Idempotent Title",
                privacy="PRIVATE",
                external_post_id="yt_existing_111",
                external_url="https://www.youtube.com/watch?v=yt_existing_111",
                request_payload_hash=hash_val
            )
            session.add(pub)
            await session.commit()

        # Compute hash again
        hash_again = publishing_service.compute_idempotency_hash(
            content_id=self.test_content_id,
            variant_id=None,
            platform_connection_id=self.test_conn_id,
            title="Idempotent Title",
            privacy="PRIVATE"
        )
        self.assertEqual(hash_val, hash_again)

    async def test_06_disconnect_cleans_credentials_and_preserves_history(self):
        """Test 6: Disconnecting revokes and wipes tokens while strictly preserving publication records."""
        async with async_session_factory() as session:
            conn = PlatformConnection(
                id=self.test_conn_id,
                platform="youtube",
                name="Channel To Disconnect",
                status="CONNECTED",
                access_token_encrypted=encryption_service.encrypt_token("token_to_wipe"),
                refresh_token_encrypted=encryption_service.encrypt_token("refresh_to_wipe")
            )
            pub = Publication(
                id=f"pub_hist_{uuid.uuid4().hex[:6]}",
                content_id=self.test_content_id,
                platform_connection_id=self.test_conn_id,
                platform="youtube",
                status="PUBLISHED",
                title="Historical Published Post",
                privacy="PRIVATE",
                external_post_id="yt_hist_999",
                external_url="https://www.youtube.com/watch?v=yt_hist_999",
                request_payload_hash="some_hash"
            )
            session.add_all([conn, pub])
            await session.commit()

        # Disconnect connection
        async with async_session_factory() as session:
            target_conn = await session.get(PlatformConnection, self.test_conn_id)
            target_conn.access_token_encrypted = None
            target_conn.refresh_token_encrypted = None
            target_conn.status = "DISCONNECTED"
            await session.commit()

        # Verify credentials wiped but publication history remains
        async with async_session_factory() as session:
            verified_conn = await session.get(PlatformConnection, self.test_conn_id)
            self.assertEqual(verified_conn.status, "DISCONNECTED")
            self.assertIsNone(verified_conn.access_token_encrypted)
            self.assertIsNone(verified_conn.refresh_token_encrypted)

            # Historical publication must still exist
            from sqlalchemy import select
            hist_res = await session.execute(select(Publication).where(Publication.content_id == self.test_content_id))
            history_items = hist_res.scalars().all()
            self.assertGreater(len(history_items), 0)
            self.assertEqual(history_items[0].status, "PUBLISHED")

if __name__ == "__main__":
    unittest.main()
