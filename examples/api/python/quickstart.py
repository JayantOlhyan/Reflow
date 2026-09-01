#!/usr/bin/env python3
"""
Reflow Python SDK Quickstart Example.
Demonstrates: API key auth, text ingest, async job polling, governance evaluation, publication, and analytics.
"""

import sys
import os

# Add packages/python-sdk to path
sdk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../packages/python-sdk"))
sys.path.insert(0, sdk_path)

from reflow import ReflowClient

def main():
    api_key = os.environ.get("REFLOW_API_KEY", "reflow_live_quickstart_key")
    client = ReflowClient(api_key=api_key, base_url="http://localhost:8000/api/v1")

    print("1. Creating text content item...")
    content = client.content.create_text(
        title="Python SDK Quickstart Post",
        raw_text="Reflow Public API allows seamless automated content creation and multi-platform publishing."
    )
    content_id = content["id"]
    print(f"   Created Content ID: {content_id}")

    print("2. Triggering AI clip discovery (202 Accepted)...")
    clip_job = client.clips.discover(content_id)
    print(f"   Job Enqueued: {clip_job['job_id']}")

    print("3. Polling job completion...")
    job_res = client.jobs.wait(clip_job["job_id"], timeout=10, poll_interval=1.0)
    print(f"   Job Status: {job_res['status']}")

    print("4. Evaluating governance quality control...")
    gov = client.governance.evaluate(content_id)
    print(f"   Governance Status: {gov.get('status', 'PASSED')}")

    print("5. Creating and publishing social post...")
    pub = client.publications.create(
        content_id=content_id,
        platform="INSTAGRAM",
        post_type="REEL",
        caption="Automated release with Reflow Python SDK! #Reflow",
        idempotency_key=f"quickstart_pub_{content_id}"
    )
    print(f"   Created Publication ID: {pub['id']}")

    pub_dispatch = client.publications.publish(pub["id"])
    print(f"   Publication Job Enqueued: {pub_dispatch['job_id']}")

    print("Reflow Python SDK Quickstart Workflow Completed Successfully!")

if __name__ == "__main__":
    main()
