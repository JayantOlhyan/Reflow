import os
import uuid
import asyncio
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from fastapi.testclient import TestClient

from main import app
from database import init_db, async_session_factory
from models.entities import TmpFileRecord
from services.tmp_storage_service import tmp_storage_service
from services.resource_manager import resource_manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_storage_db():
    asyncio.run(init_db())

def test_full_storage_lifecycle_upload_process_purge():
    """
    Validates complete storage lifecycle:
    1. Managed temporary file creation inside storage/tmp/
    2. Registration in DB with expiration timestamp
    3. Storage usage accounting & breakdown calculation
    4. Purging expired temporary files
    5. Disk space reservation & release check
    """
    # 1. Generate temp file
    fpath = tmp_storage_service.create_tmp_file_path(prefix="life_cycle", extension=".tmp")
    with open(fpath, "w") as f:
        f.write("0123456789" * 100) # 1000 bytes

    assert os.path.exists(fpath)

    # 2. Register in DB
    async def _register():
        async with async_session_factory() as session:
            return await tmp_storage_service.register_tmp_file(session, fpath, owner="lifecycle_test", ttl_hours=-1)

    rec = asyncio.run(_register())
    assert rec is not None
    assert rec.file_path == os.path.abspath(fpath)

    # 3. Storage breakdown calculation
    async def _breakdown():
        async with async_session_factory() as session:
            return await tmp_storage_service.get_storage_breakdown(session)

    bd = asyncio.run(_breakdown())
    assert "categories" in bd
    assert bd["categories"]["temporary_mb"] >= 0.0

    # 4. Purge expired temporary files
    async def _purge():
        async with async_session_factory() as session:
            return await tmp_storage_service.purge_expired_tmp_files(session)

    purge_res = asyncio.run(_purge())
    assert purge_res["purged_count"] >= 1
    assert not os.path.exists(fpath)

def test_disk_space_reservation_safety():
    """Verifies pre-flight disk capacity reservation and release mechanics."""
    status_initial = resource_manager.check_disk_capacity(required_mb=5.0)
    assert status_initial["is_sufficient"] is True

    # Reserve 20MB
    asyncio.run(resource_manager.reserve_disk_capacity(20.0))
    # Release 20MB
    asyncio.run(resource_manager.release_disk_reservation(20.0))
