# Final measurement numbers (validated records)

All numbers are **medians over 5 repetitions** from schema-v1 records
that PASS `scripts/measurement-schema/validate.py` (re-checked on load).
Site `dev_device`, per-run host introspection embedded in every record;
throughput in MB/s (1 MB = 1e6 bytes). Cross-engine comparison of
*different workloads* (scan vs full parse) is NOT apples-to-apples —
comparability notes live in the P4 bottleneck report.

## v8

- runs: zuu-20261112010521-0340a72
- git: 0340a72 — library: saq_baseline 24.19.0 (node 24.19.0 (v8 13.6.233.17-node.51))

| corpus | result | MB/s | cv |
|---|---|---:|---:|
| checker_batch | `v8/body-parse/checker_batch` | 150.7 | 0.6% |
| checker_batch | `v8/store-read/checker_batch` | 149.2 | 0.7% |
| checker_batch | `v8/export-stringify/checker_batch` | 274.1 | 0.7% |
| saq_payload_v1 | `v8/body-parse/saq_payload_v1` | 455.6 | 1.2% |
| saq_payload_v1 | `v8/store-read/saq_payload_v1` | 458.3 | 0.5% |
| saq_payload_v1 | `v8/export-stringify/saq_payload_v1` | 535.7 | 0.4% |
| synthetic_100k | `v8/body-parse/synthetic_100k` | 180.3 | 1.4% |
| synthetic_100k | `v8/store-read/synthetic_100k` | 177.4 | 1.6% |
| synthetic_100k | `v8/export-stringify/synthetic_100k` | 326.7 | 3.4% |
| synthetic_10k | `v8/body-parse/synthetic_10k` | 185.3 | 0.5% |
| synthetic_10k | `v8/store-read/synthetic_10k` | 187.6 | 0.5% |
| synthetic_10k | `v8/export-stringify/synthetic_10k` | 387.0 | 0.4% |
| synthetic_1k | `v8/body-parse/synthetic_1k` | 237.6 | 1.1% |
| synthetic_1k | `v8/store-read/synthetic_1k` | 241.2 | 0.5% |
| synthetic_1k | `v8/export-stringify/synthetic_1k` | 420.1 | 0.7% |
| synthetic_1mb | `v8/body-parse/synthetic_1mb` | 179.0 | 2.1% |
| synthetic_1mb | `v8/store-read/synthetic_1mb` | 181.7 | 0.5% |
| synthetic_1mb | `v8/export-stringify/synthetic_1mb` | 301.2 | 2.2% |

## ze_wasm64

- runs: zuu-20261112010545-c1c91ce
- git: c1c91ce* — library: ze_json 0.1.0 (node 24.19.0 (wasm64 C-ABI parser, ABI v3))

| corpus | result | MB/s | cv |
|---|---|---:|---:|
| checker_batch | `ze-parser/wasm-parse-full/checker_batch` | 8.2 | 4.5% |
| saq_payload_v1 | `ze-parser/wasm-parse-full/saq_payload_v1` | 21.4 | 0.7% |
| synthetic_100k | `ze-parser/wasm-parse-full/synthetic_100k` | 10.1 | 0.8% |
| synthetic_10k | `ze-parser/wasm-parse-full/synthetic_10k` | 10.2 | 2.1% |
| synthetic_1k | `ze-parser/wasm-parse-full/synthetic_1k` | 15.2 | 1.9% |
| synthetic_1mb | `ze-parser/wasm-parse-full/synthetic_1mb` | 9.8 | 4.9% |

