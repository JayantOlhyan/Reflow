# Reflow — Incident Management & Runbook Guide

Reflow features an incident management and alert evaluation engine designed for self-hosted operators.

---

## 1. Incident Lifecycle & Statuses

Incidents progress through 5 explicit states:
1. `OPEN`: Incident automatically created from repeated job/health failures.
2. `INVESTIGATING`: Incident acknowledged by an operator (`POST /api/system/incidents/{id}/acknowledge`).
3. `MITIGATED`: Temporary mitigation applied.
4. `RESOLVED`: Incident resolved by operator. Requires a **mandatory resolution explanation note** (`POST /api/system/incidents/{id}/resolve`).
5. `CLOSED`: Incident closed and archived.

---

## 2. Automatic Deduplication & Grouping

To prevent alert fatigue and 100 duplicate incident records during recurring job failures:
- Failures occurring for the same `component` and `error_code` within a **15-minute window** are automatically grouped into a single `OPEN` incident.
- Affected resources (`affected_jobs`, `affected_content`) and recurrence counts are updated dynamically.

---

## 3. Severity Levels

- `CRITICAL`: Complete system or primary database unavailability.
- `HIGH`: Multi-platform publishing outage, storage write failure, or repeated job failures.
- `MEDIUM`: Single platform API rate limit or transient network error.
- `LOW`: Minor performance degradation or non-blocking background sync delay.
- `INFO`: Informational system state transition notice.

---

## 4. Declarative Alert Rules & Cooldown

Operators can configure declarative `AlertRule` records. When condition thresholds are crossed (e.g. `OPEN_INCIDENTS >= 1`), in-app `Notification` alerts or outbound Webhooks are dispatched. A configurable cooldown window (`cooldown_minutes`, default: 15m) suppresses repeated alert spam.
