import time
import requests
from typing import Dict, Any, List, Optional, Generator

class ReflowError(Exception):
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

class AuthenticationError(ReflowError): pass
class AuthorizationError(ReflowError): pass
class ValidationError(ReflowError): pass
class RateLimitError(ReflowError): pass
class NotFoundError(ReflowError): pass
class ConflictError(ReflowError): pass
class ServerError(ReflowError): pass

def _raise_for_status(response: requests.Response):
    if response.status_code < 400:
        return
    try:
        data = response.json()
        err = data.get("error", {})
        code = err.get("code", "UNKNOWN_ERROR")
        msg = err.get("message", response.text)
    except Exception:
        code = "HTTP_ERROR"
        msg = response.text

    status = response.status_code
    if status == 401:
        raise AuthenticationError(msg, code, status)
    elif status == 403:
        raise AuthorizationError(msg, code, status)
    elif status == 404:
        raise NotFoundError(msg, code, status)
    elif status == 409:
        raise ConflictError(msg, code, status)
    elif status in (400, 422):
        raise ValidationError(msg, code, status)
    elif status == 429:
        raise RateLimitError(msg, code, status)
    elif status >= 500:
        raise ServerError(msg, code, status)
    else:
        raise ReflowError(msg, code, status)

class ContentModule:
    def __init__(self, client: 'ReflowClient'): self.client = client
    def list(self, page: int = 1, page_size: int = 20, search: Optional[str] = None, type: Optional[str] = None) -> Dict[str, Any]:
        return self.client._request("GET", "/content", params={"page": page, "page_size": page_size, "search": search, "type": type})
    def list_all(self, search: Optional[str] = None, type: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
        page = 1
        while True:
            res = self.list(page=page, page_size=50, search=search, type=type)
            items = res.get("items", [])
            for item in items:
                yield item
            if page * 50 >= res.get("total", 0) or not items:
                break
            page += 1
    def get(self, id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/content/{id}")
    def create_text(self, title: str, raw_text: str) -> Dict[str, Any]:
        return self.client._request("POST", "/content/text", json={"title": title, "raw_text": raw_text})
    def upload(self, file_path: str, title: Optional[str] = None) -> Dict[str, Any]:
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"title": title} if title else {}
            return self.client._request("POST", "/content/upload", files=files, data=data)
    def delete(self, id: str) -> Dict[str, Any]:
        return self.client._request("DELETE", f"/content/{id}")

class ClipsModule:
    def __init__(self, client: 'ReflowClient'): self.client = client
    def discover(self, content_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/content/{content_id}/clips/discover")
    def list(self, content_id: str) -> List[Dict[str, Any]]:
        return self.client._request("GET", f"/content/{content_id}/clips")
    def get(self, clip_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/clips/{clip_id}")
    def generate(self, clip_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/clips/{clip_id}/generate")

class CarouselsModule:
    def __init__(self, client: 'ReflowClient'): self.client = client
    def create(self, content_id: str, title: str, theme: str, slides: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.client._request("POST", f"/content/{content_id}/carousels", json={"title": title, "theme": theme, "slides": slides})
    def list(self, content_id: str) -> List[Dict[str, Any]]:
        return self.client._request("GET", f"/content/{content_id}/carousels")
    def get(self, id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/carousels/{id}")
    def generate(self, id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/carousels/{id}/generate")
    def export(self, id: str, format: str = "pdf") -> Dict[str, Any]:
        return self.client._request("POST", f"/carousels/{id}/export", params={"format": format})

class GovernanceModule:
    def __init__(self, client: 'ReflowClient'): self.client = client
    def evaluate(self, content_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/content/{content_id}/governance/evaluate")
    def get(self, content_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/content/{content_id}/governance")

class PublicationsModule:
    def __init__(self, client: 'ReflowClient'): self.client = client
    def create(self, content_id: str, platform: str, post_type: str, caption: str, title: Optional[str] = None, scheduled_at: Optional[str] = None, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        return self.client._request("POST", "/publications", json={"content_id": content_id, "platform": platform, "post_type": post_type, "caption": caption, "title": title, "scheduled_at": scheduled_at}, headers=headers)
    def publish(self, publication_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/publications/{publication_id}/publish")

class AnalyticsModule:
    def __init__(self, client: 'ReflowClient'): self.client = client
    def overview(self) -> Dict[str, Any]:
        return self.client._request("GET", "/analytics/overview")
    def get_content(self, content_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/analytics/content/{content_id}")

class JobsModule:
    def __init__(self, client: 'ReflowClient'): self.client = client
    def get(self, job_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/jobs/{job_id}")
    def wait(self, job_id: str, timeout: int = 60, poll_interval: float = 2.0) -> Dict[str, Any]:
        start = time.time()
        while time.time() - start < timeout:
            res = self.get(job_id)
            status = res.get("status")
            if status in ("SUCCEEDED", "FAILED", "STALE"):
                return res
            time.sleep(poll_interval)
        raise TimeoutError(f"Job '{job_id}' timed out after {timeout} seconds.")

class ReflowClient:
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000/api/v1", timeout: int = 30, max_retries: int = 3):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}", "Accept": "application/json"})

        self.content = ContentModule(self)
        self.clips = ClipsModule(self)
        self.carousels = CarouselsModule(self)
        self.governance = GovernanceModule(self)
        self.publications = PublicationsModule(self)
        self.analytics = AnalyticsModule(self)
        self.jobs = JobsModule(self)

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None, files: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Any:
        url = f"{self.base_url}{path}"
        req_headers = dict(self.session.headers)
        if headers:
            req_headers.update(headers)

        attempts = 0
        while attempts <= self.max_retries:
            attempts += 1
            try:
                res = self.session.request(method=method, url=url, params=params, json=json, data=data, files=files, headers=req_headers, timeout=self.timeout)
                if res.status_code in (429, 502, 503, 504) and attempts <= self.max_retries:
                    retry_after = float(res.headers.get("Retry-After", 1.0))
                    time.sleep(retry_after)
                    continue
                _raise_for_status(res)
                return res.json() if res.content else {}
            except (requests.ConnectionError, requests.Timeout) as e:
                if attempts > self.max_retries:
                    raise ServerError(f"Network request failed: {str(e)}", code="NETWORK_ERROR", status_code=503)
                time.sleep(1.0)
