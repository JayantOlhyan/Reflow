# Phase 18 Audit — Real Reflow Ecosystem & Integration Hub

## 1. Executive Summary

Phase 17 established the core plugin contracts (`BasePlugin`, `BasePlatformConnectorPlugin`, etc.) and the runtime `PluginRegistry` for discovering and isolating built-in and local file-system plugins (`./plugins/<folder>`). However, Reflow lacks ecosystem infrastructure for decentralized plugin catalog discovery, package checksum verification, dependency tree resolution, circular dependency detection, secret masking, explicit permission consent, safe rollback on update failures, and ecosystem management UI.

This audit evaluates current capabilities, identifies security/update/dependency risks, and outlines the architecture for Phase 18.

---

## 2. Current Plugin Lifecycle Audit

Currently, plugins have a basic runtime lifecycle managed by `PluginRegistry`:
1. **Discovery**: `discover_local_plugins()` scans local subdirectories under `./plugins` looking for `plugin.json`.
2. **Registration**: `register()` checks `manifest.api_version == PLUGIN_API_VERSION` and stores the `BasePlugin` instance in `self._plugins`.
3. **State Management**: `enable_plugin(id)` and `disable_plugin(id)` mutate in-memory set `self._disabled`.
4. **Health Checks**: `health_check(id)` executes isolated `asyncio.wait_for(plugin.health_check(), timeout=5.0)`.

### Missing Lifecycle Infrastructure:
- **No Catalog Discovery**: Users cannot browse or search external/community plugins.
- **No Remote Package Installation Flow**: No package tarball/zip download, extraction, or checksum verification mechanism.
- **No Persistence**: Enabled/disabled state resets on process restart if not stored in DB.
- **No Version Tracking & Update Check**: No capability to compare installed plugin versions against remote catalog versions.
- **No Uninstall & Data Isolation Standard**: Uninstalling a plugin does not audit dependent items or track plugin usage statistics across connections/publications.

---

## 3. Current Installation & Versioning Mechanics

- **Local Discovery Only**: Plugins must be manually copied into `./plugins/` on the server filesystem.
- **Exact API Version Match**: Manifest specifies `api_version`, but semantic version compatibility expressions (e.g. `>=1.0.0, <2.0.0`) are missing.
- **No Package Distribution Schema**: No standardized archive format (`.zip` / `.tar.gz` with `manifest.json` and SHA-256 checksum).

---

## 4. Identified Risks & Security Gaps

| Area | Current Risk / Limitation | Proposed Phase 18 Fix |
|---|---|---|
| **RCE & Untrusted Remote Code** | Downloading code from unverified URLs could cause RCE. | Decentralized static catalog with SHA-256 checksum verification; prohibit arbitrary remote script execution. Require local or signed catalog sources. |
| **Silent Permission Elevation** | Plugins execute with process privileges without explicit UI warning. | Interactive 7-step UI installation modal with explicit permission review (`CONTENT_READ`, `NETWORK_ACCESS`, etc.) and security status badges (`OFFICIAL`, `COMMUNITY`, `LOCAL`). |
| **Secret Leaks** | Plugin secrets (API keys, tokens) could be exposed in API endpoints or logs. | Secret schema tagging (`is_secret: True`), payload sanitization in API responses, redacted logging, and DB encryption. |
| **Broken Update Inconsistency** | A failed update leaves the system in a broken or half-updated state. | Atomic update staging with automated rollback to previous version backup if health check fails. |
| **Circular & Missing Dependencies** | Installing Plugin A requiring Plugin B (or A→B→A) crashes runtime. | Directed graph dependency validation with Cycle Detection before staging installation. |
| **SSRF via Remote Registries** | Custom `PLUGIN_REGISTRY_URL` could target `localhost` or internal cloud metadata APIs. | Enforce SSRF domain validation (blocking private/loopback/Docker IPs) and require HTTPS. |
| **Offline System Breakdown** | Loss of internet/registry connectivity breaks installed plugins. | Offline mode: installed plugins must operate normally with fallback registry caching. |

---

## 5. Architectural Objectives for Phase 18

1. **Decentralized Static Registry Catalog (`registry/registry.json`)**: Version-controlled catalog format supporting official and custom registry URLs (`PLUGIN_REGISTRY_URL`).
2. **Schema & Registry Validation**: Strict schema validator (`scripts/validate-registry.py`) checking semantic versions, checksums, duplicate IDs, and compatibility.
3. **Ecosystem & Catalog REST API**: Endpoints for discovering, searching, filtering, installing, configuring, updating, rolling back, and uninstalling plugins with audit logging.
4. **Ecosystem UI (`/ecosystem`)**: Rich discovery catalog with search, category filtering (`Platform`, `AI`, `Storage`, `Workflow`, `Media`), official/community badges, security warnings, permission breakdown, dependency tree visualization, and usage statistics.
5. **Dynamic System Integration**: Platform connectors, AI providers, storage drivers, and workflow actions dynamically populate `/connections`, `/settings`, and `/workflows` directly from registered plugins without hardcoded discovery.
6. **Robust Testing & Telemetry**: Pytest coverage for circular dependencies, checksum mismatches, SSRF blocking, offline operation, secret redaction, and rollback, plus system health telemetry metrics.
