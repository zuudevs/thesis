# Measurement Record Schema

`measurement.schema.json` — single source of truth for every measurement record
(benchmark/test, ze_json C++ or saq-report Node.js). Design rationale: `docs/project/plans.md` §3;
validation rules & usage: `AGENTS.md` §4.

Validate a record (stdlib-only, no dependencies):

    python scripts/measurement-schema/validate.py <record.json>   # exit 0 = PASS

Records without a per-result `rationale` (`purpose` + `basis_papers[]`) are invalid —
they must never drive analysis. Converter from raw google-benchmark output:
`scripts/measurement-schema/convert-gbench.py`; analyzer: `scripts/analyze_measurement/main.py`.
