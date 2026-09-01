#!/usr/bin/env python3
import os
import sys
import json
import re

REQUIRED_FIELDS = [
    "id", "name", "version", "description", "author", "repository",
    "license", "plugin_type", "api_version", "reflow_version",
    "capabilities", "permissions", "checksum", "source_type"
]

VALID_PLUGIN_TYPES = [
    "PLATFORM", "AI_PROVIDER", "STORAGE", "MEDIA_PROCESSOR", "ANALYTICS", "WORKFLOW_ACTION"
]

VALID_PERMISSIONS = [
    "CONTENT_READ", "CONTENT_WRITE", "PUBLISH", "ANALYTICS_READ",
    "STORAGE_READ", "STORAGE_WRITE", "NETWORK_ACCESS"
]

VALID_SOURCE_TYPES = ["OFFICIAL", "COMMUNITY", "LOCAL"]

SEMVER_REGEX = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$")

def validate_registry(file_path: str) -> bool:
    if not os.path.exists(file_path):
        print(f"❌ Registry file not found: {file_path}")
        return False

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Invalid JSON format in {file_path}: {e}")
        return False

    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        print("❌ 'plugins' must be an array.")
        return False

    seen_ids = set()
    errors = []

    for idx, item in enumerate(plugins):
        prefix = f"Plugin[{idx}]"

        # Required fields check
        for field in REQUIRED_FIELDS:
            if field not in item:
                errors.append(f"{prefix}: Missing required field '{field}'")

        pid = item.get("id")
        if pid:
            if pid in seen_ids:
                errors.append(f"{prefix}: Duplicate plugin ID '{pid}'")
            seen_ids.add(pid)
            if not re.match(r"^[a-z0-9-]+$", pid):
                errors.append(f"{prefix}: Invalid ID format '{pid}'. Must be lowercase alphanumeric with hyphens.")

        # Semver validation
        ver = item.get("version")
        if ver and not SEMVER_REGEX.match(ver):
            errors.append(f"{prefix} ({pid}): Invalid version '{ver}'. Must be valid semver (e.g. 1.0.0).")

        # Plugin type validation
        ptype = item.get("plugin_type")
        if ptype and ptype not in VALID_PLUGIN_TYPES:
            errors.append(f"{prefix} ({pid}): Invalid plugin_type '{ptype}'. Allowed: {VALID_PLUGIN_TYPES}")

        # Source type validation
        stype = item.get("source_type")
        if stype and stype not in VALID_SOURCE_TYPES:
            errors.append(f"{prefix} ({pid}): Invalid source_type '{stype}'. Allowed: {VALID_SOURCE_TYPES}")

        # Permissions validation
        perms = item.get("permissions", [])
        if isinstance(perms, list):
            for perm in perms:
                if perm not in VALID_PERMISSIONS:
                    errors.append(f"{prefix} ({pid}): Invalid permission '{perm}'. Allowed: {VALID_PERMISSIONS}")
        else:
            errors.append(f"{prefix} ({pid}): 'permissions' must be an array.")

        # Checksum validation (64-char hex)
        checksum = item.get("checksum")
        if checksum and not re.match(r"^[a-fA-F0-9]{64}$", checksum):
            errors.append(f"{prefix} ({pid}): Invalid SHA-256 checksum format.")

    if errors:
        print(f"❌ Registry validation failed with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        return False

    print(f"✅ Registry schema validation passed cleanly ({len(plugins)} valid plugins).")
    return True

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "registry/registry.json"
    success = validate_registry(path)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
