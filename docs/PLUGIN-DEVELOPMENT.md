# Reflow — Plugin Development Guide

This guide explains how to develop, test, and publish custom plugins for the Reflow Content Operating System.

---

## 1. Overview & Plugin Architecture

Reflow uses a contract-driven plugin architecture. Plugins allow developers to add new social platforms, AI provider models, storage backends, media transcoders, analytics providers, and workflow automation actions without altering core Reflow code.

```
                          ┌────────────────────────┐
                          │    Reflow Core API     │
                          └───────────┬────────────┘
                                      │
                          ┌───────────▼────────────┐
                          │     PluginRegistry     │
                          └───────────┬────────────┘
                                      │
     ┌────────────────┬───────────────┼───────────────┬────────────────┐
     │                │               │               │                │
┌────▼─────┐    ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐    ┌─────▼──────┐
│ PLATFORM │    │AI_PROVIDER│   │  STORAGE  │   │   MEDIA   │    │ WORKFLOW   │
│ Plugin   │    │  Plugin   │   │  Plugin   │   │ Processor │    │   Action   │
└──────────┘    └───────────┘   └───────────┘   └───────────┘    └────────────┘
```

---

## 2. Plugin Manifest (`plugin.json`)

Every plugin directory must contain a `plugin.json` manifest:

```json
{
  "id": "custom-social-connector",
  "name": "Custom Social Connector",
  "version": "1.0.0",
  "description": "Custom platform connector for Reflow.",
  "author": "Developer Name",
  "type": "PLATFORM",
  "entrypoint": "plugin:CustomPlatformPlugin",
  "api_version": "1.0.0",
  "capabilities": ["video", "image", "text", "scheduling"],
  "permissions": ["PUBLISH", "NETWORK_ACCESS"],
  "configuration": {
    "api_key": "string"
  }
}
```

---

## 3. Creating a Plugin using the CLI

Reflow includes a starter CLI generator script:

```bash
python scripts/create-plugin.py my-platform platform
```

This generates a complete starter template under `plugins/my-platform/`:
- `plugin.json` (manifest)
- `plugin.py` (entrypoint class)
- `README.md` (documentation)

---

## 4. Plugin Contracts

### 4.1 Platform Plugin (`PLATFORM`)
Inherit from `BasePlatformConnectorPlugin`:
```python
from plugins.contracts.platform_contract import BasePlatformConnectorPlugin
from connectors.base import PlatformCapabilities

class MyPlatformPlugin(BasePlatformConnectorPlugin):
    def get_capabilities(self) -> PlatformCapabilities:
        return PlatformCapabilities(video_upload=True, image_upload=True, text_post=True)

    def validate_metadata(self, metadata: dict):
        return True, None

    async def publish_text(self, metadata: dict, access_token: str):
        return {"status": "published", "external_post_id": "123", "url": "https://example.com/p/123"}
```

### 4.2 AI Provider Plugin (`AI_PROVIDER`)
Inherit from `BaseAIProviderPlugin`:
```python
from plugins.contracts.ai_contract import BaseAIProviderPlugin

class MyAIPlugin(BaseAIProviderPlugin):
    async def generate_platform(self, platform, brief, segments=None, tone="professional"):
        return {"platform": platform, "text_content": "AI generated copy."}
```

---

## 5. Security & Isolation

- **Permissions Model**: Plugins only receive declared permissions (`CONTENT_READ`, `PUBLISH`, `STORAGE_READ`, `NETWORK_ACCESS`).
- **Error Isolation**: Failing plugins are wrapped in try/except blocks; a plugin crash will never take down Reflow core API services.
- **Explicit Loading**: Only local trusted plugins in `./plugins` or installed Python packages are loaded. Arbitrary remote code execution is strictly prohibited.
