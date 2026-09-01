# Reflow Hardware & Capacity Planning Guide

## Recommended Hardware Profiles

| Hardware Profile | Cores / RAM | Recommended Setting Overrides | Workload Capacity |
| :--- | :--- | :--- | :--- |
| **Small VM** (Raspberry Pi 4 / 2-Core VPS) | 2 Cores / 4 GB RAM | `MEDIA_WORKER_CONCURRENCY=1`<br>`MAX_STORAGE_GB=20` | ~50 videos/day, single creator |
| **Standard VM** (Self-Hosted Node) | 4 Cores / 8 GB RAM | `MEDIA_WORKER_CONCURRENCY=2`<br>`MAX_STORAGE_GB=50` | ~250 videos/day, small team |
| **Heavy Workstation** (Dedicated Server) | 8+ Cores / 16+ GB RAM | `MEDIA_WORKER_CONCURRENCY=4`<br>`MAX_STORAGE_GB=200` | ~1,000+ videos/day, agency |

---

## Storage Directory Allocation Strategy
- `storage/uploads/`: Original ingested media assets.
- `storage/variants/`: Transcoded 9:16, 1:1, 4:5, 16:9 video variants.
- `storage/clips/`: Highlight clips and captioned variants.
- `storage/carousels/`: Generated slide PNG/PDF assets.
- `storage/exports/`: Final rendered social platform export packages.
- `storage/tmp/`: Managed temporary files with scheduled auto-cleanup.
