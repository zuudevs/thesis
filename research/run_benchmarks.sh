#!/usr/bin/env bash
# ============================================================================
#  run_benchmarks.sh — Runner benchmark SEKALI-JALAN (Linux / server SAQ)
# ============================================================================
#  Kontrak eksekusi IDENTIK dengan research/run_benchmarks.ps1 (Windows) —
#  lihat header berkas itu untuk penjelasan lengkap. Dipakai di server SAQ:
#
#    export SAMPLE=/path/to/sample   # korpus asli (sha256 = manifest ze_json)
#    export RAW=/path/to/raw         # folder artefak
#    ./research/run_benchmarks.sh                          # full (5 repetisi)
#    ./research/run_benchmarks.sh --repetitions 7
#    ./research/run_benchmarks.sh --quick                  # 3 repetisi (sanity)
#    ./research/run_benchmarks.sh --skip-ze-json           # hanya saq-report
#    ./research/run_benchmarks.sh --skip-saq-report        # hanya ze_json
#    ./research/run_benchmarks.sh --skip-ze-json-js        # tanpa benchmark JS
# ============================================================================
set -euo pipefail

REPS=5
SKIP_ZE_JSON=0
SKIP_SAQ_REPORT=0
SKIP_ZE_JSON_JS=0
SKIP_CORPUS=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --quick) REPS=3; shift ;;
        --repetitions) REPS="$2"; shift 2 ;;
        --skip-ze-json) SKIP_ZE_JSON=1; shift ;;
        --skip-saq-report) SKIP_SAQ_REPORT=1; shift ;;
        --skip-ze-json-js) SKIP_ZE_JSON_JS=1; shift ;;
        --skip-corpus-preflight) SKIP_CORPUS=1; shift ;;
        *) echo "argumen tak dikenal: $1" >&2; exit 2 ;;
    esac
done

WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
ZE_REPO="$WORKSPACE/ze_json"
SAQ_REPO="$WORKSPACE/saq-report"

for var in SAMPLE RAW; do
    if [[ -z "${!var:-}" ]]; then
        echo "Environment $var belum di-set. Contoh: export $var=<path>" >&2
        exit 2
    fi
done
echo "SAMPLE = $SAMPLE"
echo "RAW    = $RAW"

# ---------------------------------------------------------------------------
# 1. Preflight korpus terpadu
# ---------------------------------------------------------------------------
if [[ $SKIP_CORPUS -eq 0 ]]; then
    echo ""
    echo "=== [1/5] Preflight korpus terpadu ==="

    echo "-- corpus install --skip-existing"
    (cd "$ZE_REPO" && python3 scripts/corpus/main.py install --skip-existing)

    echo "-- saq-report generate + verify samples"
    (cd "$SAQ_REPO" && node benchmark/generate-samples.js && node benchmark/verify-samples.js)

    echo "-- corpus scan + verify"
    (cd "$ZE_REPO" && python3 scripts/corpus/main.py scan && python3 scripts/corpus/main.py verify)
else
    echo ""
    echo "=== [1/5] Preflight korpus DILEWATI (--skip-corpus-preflight) ==="
fi

# ---------------------------------------------------------------------------
# 2. ze_json — 5 export benchmark (repetisi terstandar)
# ---------------------------------------------------------------------------
if [[ $SKIP_ZE_JSON -eq 0 ]]; then
    echo ""
    echo "=== [2/5] ze_json benchmark (repetisi=$REPS) ==="
    (cd "$ZE_REPO" && cmake --preset native-release -DZE_BENCH_REPETITIONS="$REPS")
    for t in parser_benchmark scanner_benchmark session_benchmark span_iso_benchmark corpus_benchmark; do
        echo "-- export_benchmark_$t"
        (cd "$ZE_REPO" && cmake --build build/native-release --target "export_benchmark_$t")
    done
else
    echo ""
    echo "=== [2/5] ze_json DILEWATI (--skip-ze-json) ==="
fi

# ---------------------------------------------------------------------------
# 3. saq-report — JSON.parse baseline di korpus terpadu
# ---------------------------------------------------------------------------
if [[ $SKIP_SAQ_REPORT -eq 0 ]]; then
    echo ""
    echo "=== [3/5] saq-report benchmark (JSON.parse) ==="
    (cd "$SAQ_REPO" && node benchmark/benchmark-json.js \
        --input="$SAMPLE" --out="$RAW/benchmark/saq-report")
else
    echo ""
    echo "=== [3/5] saq-report DILEWATI (--skip-saq-report) ==="
fi

# ---------------------------------------------------------------------------
# 4. ze_json_js — binding WASM vs JSON.parse di runtime Node yang sama
#    (butuh Node >= 24 / WASM memory64; script memberi pesan jelas bila tidak)
# ---------------------------------------------------------------------------
if [[ $SKIP_ZE_JSON_JS -eq 0 ]]; then
    echo ""
    echo "=== [4/5] ze_json_js benchmark (WASM vs JSON.parse) ==="
    # ze_json_core.wasm tidak ikut git (artefak build) — build dulu bila belum ada.
    if [[ ! -f "$ZE_REPO/bindings/js/ze_json_core.wasm" ]]; then
        echo "-- build wasm64 core (ze_json_core.wasm belum ada)"
        (cd "$ZE_REPO" && cmake --preset wasm64-release \
            && cmake --build build/wasm64-release --target ze_json_core)
    fi
    node "$WORKSPACE/research/benchmark_ze_json_js.mjs" \
        --input="$SAMPLE" --out="$RAW/benchmark/ze_json_js"
else
    echo ""
    echo "=== [4/5] ze_json_js DILEWATI (--skip-ze-json-js) ==="
fi

# ---------------------------------------------------------------------------
# 5. Audit — gerbang integritas artefak
# ---------------------------------------------------------------------------
echo ""
echo "=== [5/5] Audit artefak ==="
python3 "$WORKSPACE/research/audit_raw.py" --raw "$RAW"

echo ""
echo "Selesai. Artefak: $RAW/benchmark/{ze_json,saq-report,ze_json_js}/"
echo "Analisa : python3 research/analyze_benchmarks.py"
echo "Visual  : python3 research/visualize.py"
