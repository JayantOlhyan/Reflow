import os
import sys
import pytest
import asyncio
import hashlib
from fastapi.testclient import TestClient

from main import app
from database import init_db, async_session_factory
from models.entities import APIKey

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    asyncio.run(init_db())
    yield

def create_test_api_key(scopes=["*"], name="Test Key"):
    raw_key = f"reflow_live_test_{os.urandom(8).hex()}"
    hashed = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

    async def _insert():
        async with async_session_factory() as session:
            key_obj = APIKey(
                id=f"key_{os.urandom(6).hex()}",
                name=name,
                prefix=raw_key[:12],
                hashed_key=hashed,
                permissions_json=str(scopes).replace("'", '"')
            )
            session.add(key_obj)
            await session.commit()

    asyncio.run(_insert())
    return raw_key

def test_api_v1_discovery():
    res = client.get("/api/v1/")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Reflow Public API"
    assert data["version"] == "v1.0.0"
    assert "capabilities" in data

def test_api_key_auth_401_without_header():
    res = client.get("/api/v1/content")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

def test_scope_enforcement_403_rejection():
    # Key with only CONTENT_READ scope
    read_only_key = create_test_api_key(scopes=["CONTENT_READ"], name="Read Only")
    headers = {"Authorization": f"Bearer {read_only_key}"}

    # Attempt mutation (POST /api/v1/content/text)
    res = client.post("/api/v1/content/text", json={"title": "Test", "raw_text": "Text"}, headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN_SCOPE"

def test_idempotency_key_deduplication():
    key = create_test_api_key(scopes=["*"], name="Full Key")
    headers = {
        "Authorization": f"Bearer {key}",
        "Idempotency-Key": "idemp_test_key_12345"
    }

    payload = {
        "content_id": "cnt_fake_123",
        "platform_connection_id": "conn_123",
        "title": "Idempotent post",
        "description": "Post description"
    }

    # First request
    res1 = client.post("/api/v1/publications", json=payload, headers=headers)
    assert res1.status_code == 200
    pub_id1 = res1.json()["id"]

    # Repeat request with SAME key & payload
    res2 = client.post("/api/v1/publications", json=payload, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["id"] == pub_id1

    # Repeat request with SAME key but DIFFERENT payload -> 409 Conflict
    different_payload = dict(payload)
    different_payload["title"] = "Changed title payload"
    res3 = client.post("/api/v1/publications", json=different_payload, headers=headers)
    assert res3.status_code == 409
    assert "IDEMPOTENCY_CONFLICT" in res3.text

def test_async_202_job_polling_flow():
    key = create_test_api_key(scopes=["*"])
    headers = {"Authorization": f"Bearer {key}"}

    # 1. Create content
    c_res = client.post("/api/v1/content/text", json={"title": "Async Test", "raw_text": "Async video ingest content"}, headers=headers)
    content_id = c_res.json()["id"]

    # 2. Trigger clip discovery -> 202 Accepted
    disc_res = client.post(f"/api/v1/content/{content_id}/clips/discover", headers=headers)
    assert disc_res.status_code == 202
    job_id = disc_res.json()["job_id"]
    assert job_id.startswith("job_clip_disc_")

    # 3. Poll job status via GET /api/v1/jobs/{id}
    job_res = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert job_res.status_code == 200
    assert job_res.json()["id"] == job_id
    assert job_res.json()["status"] in ("QUEUED", "RUNNING", "SUCCEEDED")

def test_public_content_and_asset_apis():
    key = create_test_api_key(scopes=["CONTENT_READ", "CONTENT_WRITE"])
    headers = {"Authorization": f"Bearer {key}"}

    # Ingest text
    c_res = client.post("/api/v1/content/text", json={"title": "API Test", "raw_text": "Content body"}, headers=headers)
    assert c_res.status_code == 200
    cid = c_res.json()["id"]

    # List content
    list_res = client.get("/api/v1/content?page=1&page_size=10", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # Get detail
    det_res = client.get(f"/api/v1/content/{cid}", headers=headers)
    assert det_res.status_code == 200
    assert det_res.json()["id"] == cid

    # Delete content
    del_res = client.delete(f"/api/v1/content/{cid}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

def test_public_governance_and_publishing_apis():
    key = create_test_api_key(scopes=["*"])
    headers = {"Authorization": f"Bearer {key}"}

    # Ingest content
    c_res = client.post("/api/v1/content/text", json={"title": "Gov Test", "raw_text": "Governance QC body"}, headers=headers)
    cid = c_res.json()["id"]

    # Evaluate governance
    gov_res = client.post(f"/api/v1/content/{cid}/governance/evaluate", headers=headers)
    assert gov_res.status_code == 200

    # Create publication
    pub_res = client.post("/api/v1/publications", json={
        "content_id": cid,
        "platform_connection_id": "conn_123",
        "title": "YouTube Short caption",
        "description": "Short description"
    }, headers=headers)
    assert pub_res.status_code == 200
    pub_id = pub_res.json()["id"]

    # Trigger publication dispatch (202 Accepted)
    trig_res = client.post(f"/api/v1/publications/{pub_id}/publish", headers=headers)
    assert trig_res.status_code == 202
    assert "job_id" in trig_res.json()

def test_python_sdk_integration():
    sdk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../packages/python-sdk"))
    if sdk_path not in sys.path:
        sys.path.insert(0, sdk_path)
    from reflow import ReflowClient

    key = create_test_api_key(scopes=["*"])
    # Instantiate Python SDK client with test key
    sdk_client = ReflowClient(api_key=key, base_url="http://testserver/api/v1")
    # Verify client initialization & sub-modules
    assert hasattr(sdk_client, "content")
    assert hasattr(sdk_client, "clips")
    assert hasattr(sdk_client, "carousels")
    assert hasattr(sdk_client, "publications")
    assert hasattr(sdk_client, "jobs")
