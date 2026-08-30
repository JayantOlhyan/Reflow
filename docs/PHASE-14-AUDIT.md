# Reflow — Phase 14: Content Governance & Quality Control Engine Audit

**Phase:** Phase 14 — Content Governance & Quality Control Engine  
**Status:** Audit Complete  

---

## 1. Current Validation & Quality Capabilities

Reflow has implemented standard checks across individual service layers through Phase 13, but they are localized and lack a centralized policy checking framework:
- **Media Transcoding Validation**: During `MEDIA_PROCESSING` and `CLIP_RENDER`, video streams are inspected using FFprobe to verify file existence and read timestamps. If corrupt, the job transitions to `FAILED` and removes temporary files.
- **Idempotency Verification**: A deterministic SHA-256 payload hash (combining content, connection, title, and privacy) is computed before publishing to avoid duplicates.
- **Connection Checks**: Scans `PlatformConnection` access tokens, attempting automatic refresh via OAuth providers, throwing `PermissionError` if refresh tokens are missing or expired.
- **Automation Safety Checks**: Evaluates daily limits and cooldown periods per rule before queuing actions.
- **Platform Capability Matching**: Asserts simple layout capability matrices (e.g. TEXT -> X/LinkedIn, VIDEO -> YouTube/Reels) to route media variants.

---

## 2. Current Approval Flows

- **Manual/Auto Approve Scopes**: Content creation flows (Repurpose Studio, Slide Generator) or Phase 13 automation rules can set scope to `REQUIRE_APPROVAL` or `AUTO_APPROVE`.
- If approval is required, publication jobs are held in `PENDING_APPROVAL` status, and wait until a user manually hits the `/approve` endpoint.

---

## 3. Missing Governance & Quality Capabilities (Gaps)

Reflow currently lacks a pre-publication quality control and validation layer:
1. **Centralized Policy Engine**: No declarative governance system (`GovernancePolicy`) to specify rule sets, severity tags (`INFO`, `WARNING`, `BLOCKING`), or target scopes.
2. **Comprehensive Media Validation**: No checks to verify video container codecs, audio streams presence, dimensions, frame rates, PDF page counts, image dimensions, or text encoding limitations.
3. **Advanced Duplicate Detection**: No checks to verify if identical content has been queued/published on the target platform within a specific timezone window, or near-duplicate check configurations.
4. **Brand Profile & Term Compliance**: No capability to declare brand profiles (`BrandProfile`) restricting forbidden terms (e.g., "guaranteed returns"), enforcing CTA inclusions, tone checks, or mention/hashtag policies.
5. **AI Quality & Claim Traceability**: No system to score copy fit, readability, or check AI-generated factual claims against source transcripts (`ContentClaim`), mapping them to source segment references.
6. **Governance Overrides Audit**: No privileged override mechanism (`GovernanceOverride`) to allow administrators to publish warning-level posts while logging reason audits.

---

## 4. Reusable Infrastructure & Capabilities

- **FFprobe Integration**: Existing calls in `media_processor` to inspect codecs and resolution can be wrapped.
- **Database Schema & Worker Queue**: The SQLite/Postgres ORM setup allows creating new tables and registering a asynchronous `QUALITY_CONTROL` task in the background worker queue.
- **Connector Definitions**: Platform limitation checks can read direct limits from connector properties.
