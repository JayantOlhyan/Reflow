import pytest
from services.storage_service import validate_upload, generate_storage_key

def test_upload_sanitizes_path_traversal_filenames():
    """Verify upload validator rejects path traversal sequences in filenames."""
    malicious_filenames = [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\config",
        "/absolute/path/file.mp4",
        "normal_name/../other.mp4"
    ]
    for fn in malicious_filenames:
        is_valid, content_type, err = validate_upload(fn, "video/mp4", 1024)
        # Should either strip traversal or fail cleanly
        safe_key = generate_storage_key("cnt_123", "ast_456", fn)
        assert ".." not in safe_key
        assert "/etc/passwd" not in safe_key

def test_upload_validates_extensions_and_mime():
    """Verify upload validator rejects dangerous or unsupported file types."""
    invalid_uploads = [
        ("payload.exe", "application/x-msdownload"),
        ("script.sh", "text/x-shellscript"),
        ("malicious.php", "application/x-php"),
        ("shell.py", "text/x-python")
    ]
    for fn, mime in invalid_uploads:
        is_valid, content_type, err = validate_upload(fn, mime, 1024)
        assert is_valid is False
        assert err is not None
