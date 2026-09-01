# Phase 17 Audit — Real Open-Source Extensibility & Plugin Ecosystem

## Executive Summary

The Phase 17 Audit evaluates the Reflow codebase across backend services, connectors, storage drivers, AI providers, media processors, automation engine, API routing, and security.

While Phases 0–16 established a robust content engine with rich capabilities (clip extraction, carousel generation, governance, analytics, automation), many core engines still rely on direct concrete class instantiations, static dictionary mappings, or hardcoded imports.

Phase 17 converts Reflow into a modular, contract-driven, open-source extensible platform using a formal **Plugin Architecture** (`PluginRegistry`, `BasePlugin`, explicit contracts, permissions, webhooks, and API key authorization).

---

## Component Audit & Coupling Analysis

### 1. Social Platform Connectors (`connectors/`)
- **Current State**: `base.py` defines `BasePlatformConnector` and `PlatformCapabilities`, but concrete platform modules (`youtube.py`, `instagram.py`, `linkedin.py`, etc.) are explicitly imported in `publishing_service.py` and `main.py`.
- **Coupling & Hardcoding**: Adding a new platform (e.g. `Threads` or `TikTok`) requires manually modifying `publishing_service.py`, `main.py`, and frontend forms.
- **Remediation**: Wrap connectors in `PLATFORM` plugins registered with `PluginRegistry`. Expose dynamic capability declarations so UI renders available platform options dynamically.

### 2. AI Intelligence Providers (`services/ai/`)
- **Current State**: `base_provider.py` defines `BaseAIProvider`. concrete classes `GeminiProvider`, `OpenAIProvider`, and `MockAIProvider` exist.
- **Coupling & Hardcoding**: `ai_service.py` switches between providers using hardcoded `if provider == "gemini"` branches.
- **Remediation**: Implement `AIProviderRegistry` and `AI_PROVIDER` plugin type. Register Gemini and OpenAI as built-in plugins. `ai_service.py` delegates to `ai_provider_registry.get_active_provider()`.

### 3. Media Storage Drivers (`services/storage_service.py`)
- **Current State**: `BaseStorageService` and `LocalStorageService` exist.
- **Coupling & Hardcoding**: Functions in `media_service.py` directly instantiate `LocalStorageService`.
- **Remediation**: Implement `BaseStorageProvider` plugin contract and `STORAGE` plugin type. Register `LocalStorage` as built-in plugin and allow pluggable S3/MinIO drivers.

### 4. Media Transcoder Engine (`services/media_service.py`)
- **Current State**: FFmpeg wrapper calls `subprocess.run` directly inside `media_service.py`.
- **Coupling & Hardcoding**: Media operations (probe, thumbnail, aspect-ratio transcode, sub-clipping) are directly bound to local FFmpeg binaries.
- **Remediation**: Define `BaseMediaProcessor` contract and `MEDIA_PROCESSOR` plugin type. Register FFmpeg processor as built-in plugin.

### 5. Analytics Engine (`services/analytics_service.py`)
- **Current State**: `analytics_service.py` directly queries platform APIs or mock data generators.
- **Coupling & Hardcoding**: Fetching metrics per platform relies on static `if/else` checks per platform ID.
- **Remediation**: Define `BaseAnalyticsProvider` contract and `ANALYTICS` plugin type. Route analytics fetching through platform plugins with `analytics` capability.

### 6. Workflow & Automation Engine (`services/automation_service.py`)
- **Current State**: Action handlers (`publish_post`, `generate_clips`, `send_notification`) are hardcoded python functions in `automation_service.py`.
- **Coupling & Hardcoding**: Developers cannot add custom workflow actions (e.g., custom webhooks, email alerts, Slack messages) without modifying `automation_service.py`.
- **Remediation**: Define `BaseWorkflowAction` contract (`WORKFLOW_ACTION` plugin type) with input/output schemas (`Pydantic`).

### 7. Security, Isolation & Permissions
- **Current State**: No sandboxing or permissions check for extensions.
- **Risks**: Unrestricted execution of arbitrary Python files could allow path traversal, arbitrary shell execution, or credential theft.
- **Remediation**:
  - Enforce explicit manifest validation (`plugin.json`).
  - Restrict loading to trusted built-in plugins and local modules in `./plugins`.
  - Introduce granular permissions: `CONTENT_READ`, `CONTENT_WRITE`, `PUBLISH`, `ANALYTICS_READ`, `STORAGE_READ`, `STORAGE_WRITE`, `NETWORK_ACCESS`.
  - Isolate plugin errors with try/except fallbacks so a failing plugin cannot crash core Reflow services.

---

## Target Extension Points Summary

| Extension Point | Plugin Type | Contract Class | Purpose | Built-in Implementations |
|---|---|---|---|---|
| Platform Connectors | `PLATFORM` | `BasePlatformConnector` | OAuth & Multi-platform publishing | YouTube, Instagram, TikTok, LinkedIn, X, Facebook, Pinterest, Threads |
| AI Providers | `AI_PROVIDER` | `BaseAIProvider` | Text generation, transcript analysis, clip discovery, carousel planning | Gemini, OpenAI, Mock |
| Storage Providers | `STORAGE` | `BaseStorageProvider` | Binary media asset persistence | LocalStorage |
| Media Processors | `MEDIA_PROCESSOR` | `BaseMediaProcessor` | Probe, thumbnail, aspect transcode, clip extraction | FFmpegMediaProcessor |
| Analytics Providers | `ANALYTICS` | `BaseAnalyticsProvider` | Metric polling & post performance tracking | PlatformAnalyticsProvider |
| Workflow Actions | `WORKFLOW_ACTION` | `BaseWorkflowAction` | Automation pipeline actions | WebhookAction, EmailAction, CustomTransformAction |

---

## Architectural Action Plan

1. **Core Plugin SDK & Architecture (`plugins/`)**:
   - `PluginManifest` Pydantic model (`plugin.json`).
   - `BasePlugin` abstract class with lifecycle (`initialize`, `shutdown`, `health_check`, `configuration_schema`).
   - `PluginRegistry` singleton with register, unregister, discover, load, enable, disable, health_check.
   - Plugin database entity (`PluginConfiguration`) and REST API endpoints (`/api/plugins`).

2. **Refactor Core Engines into Plugin Contracts**:
   - Refactor Platform connectors into `PLATFORM` plugins.
   - Refactor AI providers into `AIProviderRegistry` & `AI_PROVIDER` plugins.
   - Refactor Storage service into `STORAGE` plugins.
   - Refactor Media processing into `MEDIA_PROCESSOR` plugins.
   - Refactor Automation actions into `WORKFLOW_ACTION` plugins.

3. **Outbound Webhooks System**:
   - Database entity `WebhookEndpoint`.
   - Event bus integration (`content.created`, `content.ready`, `clip.ready`, `carousel.ready`, `publication.succeeded`, `publication.failed`, `analytics.updated`, `experiment.completed`, `automation.completed`, `governance.blocked`).
   - HMAC-SHA256 payload signing, exponential backoff retries, event ID deduplication.
   - Webhook REST API (`/api/webhooks`) & management UI (`/settings/webhooks`).

4. **Public API & API Key Security**:
   - Database entity `APIKey` with SHA-256 hashed storage.
   - Scopes (`CONTENT_READ`, `CONTENT_WRITE`, `PUBLISH`, `ANALYTICS_READ`, `AUTOMATION_READ`, `AUTOMATION_WRITE`).
   - Audit logging in `SystemLog`.
   - Public API documentation (`docs/API.md`).

5. **Developer Tooling & Examples**:
   - `packages/plugin-sdk/`: Clean exportable SDK.
   - `scripts/create-plugin.py`: Starter CLI plugin generator.
   - Example plugins (`examples/plugins/example-platform/`, `example-ai-provider/`, `example-storage/`, `example-workflow-action/`).
   - `docs/PLUGIN-DEVELOPMENT.md`.

6. **Frontend UI Integration**:
   - Plugin Management Page (`apps/web/src/app/plugins/page.tsx`).
   - Webhook Management Page (`apps/web/src/app/settings/webhooks/page.tsx`).
   - Dynamic platform rendering in `/connections` and dynamic AI provider rendering in `/settings`.

7. **Contract Testing & Quality Assurance**:
   - `apps/api/test_phase17.py`: Comprehensive test suite verifying all 90 Phase 17 specifications.
