# Final measurement numbers (validated records)

All numbers are **medians over 5 repetitions** from schema-v1 records
that PASS `scripts/measurement-schema/validate.py` (re-checked on load).
Site `dev_device`, per-run host introspection embedded in every record;
throughput in MB/s (1 MB = 1e6 bytes). Cross-engine comparison of
*different workloads* (scan vs full parse) is NOT apples-to-apples —
comparability notes live in the P4 bottleneck report.

## ze_native

- runs: zuu-20261109042022-ca8f5f4
- git: ca8f5f4 — library: ze_json 0.1.0 (C++23 clang 23.1.5 (native-release))

| corpus | result | MB/s | cv |
|---|---|---:|---:|
| checker_batch | `BM_ReferenceScan/checker_batch/repeats:5` | 700.8 | 6.4% |
| checker_batch | `BM_Scanner8/checker_batch/repeats:5` | 739.8 | 4.9% |
| saq_payload_v1 | `BM_ReferenceScan/saq/repeats:5` | 1,055.9 | 3.4% |
| saq_payload_v1 | `BM_Scanner8/saq/repeats:5` | 938.6 | 1.8% |
| synthetic_100k | `BM_ReferenceScan/synthetic_100k/repeats:5` | 734.0 | 3.6% |
| synthetic_100k | `BM_Scanner8/synthetic_100k/repeats:5` | 734.0 | 2.4% |
| synthetic_10k | `BM_ReferenceScan/synthetic_10k/repeats:5` | 758.7 | 1.3% |
| synthetic_10k | `BM_Scanner8/synthetic_10k/repeats:5` | 741.4 | 1.5% |
| synthetic_1k | `BM_ReferenceScan/synthetic_1k/repeats:5` | 998.6 | 4.9% |
| synthetic_1k | `BM_Scanner8/synthetic_1k/repeats:5` | 892.4 | 1.0% |
| synthetic_1mb | `BM_ReferenceScan/synthetic_1mb/repeats:5` | 696.3 | 3.1% |
| synthetic_1mb | `BM_Scanner8/synthetic_1mb/repeats:5` | 726.5 | 1.1% |

## v8

- runs: zuu-20261108214228-0340a72
- git: 0340a72 — library: saq_baseline 24.19.0 (node 24.19.0 (v8 13.6.233.17-node.51))

| corpus | result | MB/s | cv |
|---|---|---:|---:|
| checker_batch | `v8/body-parse/checker_batch` | 144.3 | 1.7% |
| checker_batch | `v8/store-read/checker_batch` | 135.2 | 2.8% |
| checker_batch | `v8/export-stringify/checker_batch` | 267.6 | 1.6% |
| saq_payload_v1 | `v8/body-parse/saq_payload_v1` | 391.1 | 11.8% |
| saq_payload_v1 | `v8/store-read/saq_payload_v1` | 427.1 | 1.6% |
| saq_payload_v1 | `v8/export-stringify/saq_payload_v1` | 526.0 | 1.7% |
| synthetic_100k | `v8/body-parse/synthetic_100k` | 163.8 | 13.2% |
| synthetic_100k | `v8/store-read/synthetic_100k` | 166.7 | 7.6% |
| synthetic_100k | `v8/export-stringify/synthetic_100k` | 289.2 | 2.2% |
| synthetic_10k | `v8/body-parse/synthetic_10k` | 169.3 | 2.7% |
| synthetic_10k | `v8/store-read/synthetic_10k` | 167.8 | 8.6% |
| synthetic_10k | `v8/export-stringify/synthetic_10k` | 355.9 | 1.4% |
| synthetic_1k | `v8/body-parse/synthetic_1k` | 226.0 | 8.7% |
| synthetic_1k | `v8/store-read/synthetic_1k` | 228.3 | 7.0% |
| synthetic_1k | `v8/export-stringify/synthetic_1k` | 393.2 | 5.4% |
| synthetic_1mb | `v8/body-parse/synthetic_1mb` | 168.6 | 11.2% |
| synthetic_1mb | `v8/store-read/synthetic_1mb` | 174.5 | 1.0% |
| synthetic_1mb | `v8/export-stringify/synthetic_1mb` | 261.5 | 3.5% |

## ze_wasm64

- runs: zuu-20261108221414-85afad7
- git: 85afad7 — library: ze_json 0.1.0 (node 24.19.0 (wasm64 C-ABI, ABI v1))

| corpus | result | MB/s | cv |
|---|---|---:|---:|
| checker_batch | `ze-wasm64/wasm-scan/checker_batch` | 405.2 | 1.2% |
| saq_payload_v1 | `ze-wasm64/wasm-scan/saq_payload_v1` | 688.0 | 2.0% |
| synthetic_100k | `ze-wasm64/wasm-scan/synthetic_100k` | 592.7 | 1.4% |
| synthetic_10k | `ze-wasm64/wasm-scan/synthetic_10k` | 590.5 | 4.4% |
| synthetic_1k | `ze-wasm64/wasm-scan/synthetic_1k` | 603.6 | 1.9% |
| synthetic_1mb | `ze-wasm64/wasm-scan/synthetic_1mb` | 599.5 | 1.5% |

