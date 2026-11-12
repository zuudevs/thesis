# Architecture Decision Records

ADR mencatat keputusan arsitektural penting workspace thesis beserta konteks
dan konsekuensinya. Setiap record bersifat **imutabel**: keputusan baru yang
menggantikan keputusan lama ditulis sebagai ADR baru yang merujuk ADR lama.

## Indeks

| ADR | Judul | Status |
|---|---|---|
| [0001](0001-ondemand-direction.md) | Arah on-demand untuk jalur JSON SAQ | Accepted |
| [0004](0004-corpus-saq-payload-v1.md) | Korpus `saq_payload_v1` | Accepted |
| [0005](0005-repository-readcount-sole-owner-slot.md) | `readCount()` repositori dengan slot parser sole-owner | Accepted |
| [0006](0006-mongo-cache-bytes.md) | Kandidat cache-bytes Mongo (`_cacheBytes`) | Accepted |
| [0007](0007-measurement-schema-v1-extras.md) | Measurement schema v1 + mekanisme `extras` | Accepted |

## Konvensi penomoran

Workspace thesis dan repo `ze_json` memakai **satu penomoran ADR kontinu
lintas-repo** (konvensi disepakati pada overhaul arsitektur dokumentasi
2026-11-12; juga terdokumentasi di `ze_json/docs/adr/README.md`): setiap ADR
mempertahankan nomornya asli walau hidup di repo lain. Repo ini memegang
record sisi riset/pengukuran (0001, 0004–0007); repo `ze_json` memegang
record sisi library — [0002](../../ze_json/docs/adr/0002-scanner64-swar-rejected.md)
(scanner64 SWAR sebagai default produksi — Rejected) dan
[0003](../../ze_json/docs/adr/0003-abi-v3-slot-pool.md) (permukaan parser
ABI v3 pada slot pool statis — Accepted).

## Dokumen desain terkait (bukan ADR)

- Kontrak desain lazy-access layer + keputusan D1–D3:
  [`../architecture/lazy-access-api.md`](../architecture/lazy-access-api.md).
- Protokol eksperimen ND-6:
  [`../measurement/nd6-benchmark-plan.md`](../measurement/nd6-benchmark-plan.md).
