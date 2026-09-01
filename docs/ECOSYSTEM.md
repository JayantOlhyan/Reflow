# Reflow — Decentralized Ecosystem & Integration Hub Architecture

Reflow provides a decentralized, open-source, self-hosted plugin ecosystem infrastructure. Self-hosters can discover, inspect, configure, install, update, and uninstall plugins without depending on a proprietary cloud SaaS backend.

---

## 1. Core Principles

- **Open-Source & Self-Hosted**: Reflow does not depend on a centralized cloud service. The system operates locally even if external services are unreachable.
- **Decentralized Registry**: Plugins are discovered via version-controlled static JSON catalog files (`registry/registry.json`) or custom HTTPS registry endpoints (`PLUGIN_REGISTRY_URL`).
- **Zero Arbitrary Remote Code Execution**: Direct execution of unverified remote scripts is strictly prohibited. Packages must be installed locally or verified against SHA-256 checksums.
- **Explicit Permission & Trust Model**: Permissions declared by plugins (`CONTENT_READ`, `PUBLISH`, `NETWORK_ACCESS`, etc.) must be explicitly reviewed and accepted by the user prior to installation.
- **Secret Redaction**: Plugin secret fields (API keys, OAuth tokens) are marked `is_secret`, redacted in logs and API responses (`********`), and masked in the UI.

---

## 2. Registry Catalog Format (`registry.json`)

```json
{
  "version": "1.0.0",
  "updated_at": "2026-09-01T00:00:00Z",
  "plugins": [
    {
      "id": "youtube-connector",
      "name": "YouTube Platform Connector",
      "version": "1.0.0",
      "description": "Official platform connector for YouTube video uploads and shorts.",
      "author": "Reflow Core Team",
      "repository": "https://github.com/JayantOlhyan/Reflow",
      "license": "MIT",
      "plugin_type": "PLATFORM",
      "api_version": "1.0.0",
      "reflow_version": ">=1.0.0",
      "capabilities": ["video", "text", "scheduling", "analytics"],
      "permissions": ["PUBLISH", "NETWORK_ACCESS"],
      "package": "builtin",
      "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "source_type": "OFFICIAL"
    }
  ]
}
```

---

## 3. Atomic Updates & Automated Rollback

When updating a plugin:
1. Reflow creates a state backup of the current plugin version.
2. The new package is installed and isolated health checks are executed.
3. If the health check fails, **automated rollback** restores the previous version and logs a `ROLLBACK` audit entry.

---

## 4. Offline Resilience

Reflow caches registry metadata locally with a 5-minute TTL. If network connectivity fails, installed plugins continue functioning normally, and the catalog falls back to local cache or `registry/registry.json`.
