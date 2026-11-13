#!/usr/bin/env python3
"""measurement-record validator (JSON Schema draft-07 subset, Python stdlib only).

Usage:
    python scripts/measurement-schema/validate.py <record.json> [...]

Exit codes:
    0 = every record PASSes
    1 = at least one record FAILs (or usage error)

Design notes:
- All schema rules (required keys, types, enums, consts, patterns, minItems,
  minLength, minimum, additionalProperties) are driven by
  ``schemas/measurement.schema.json`` -- do not duplicate schema semantics here.
- A record without a non-empty ``rationale`` (``purpose`` + ``basis_papers``) per
  ``results[]`` entry therefore fails automatically, per docs/project/plans.md section 3.
- Numbers compared for optimization work must come from records that pass this
  validator (see AGENTS.md section 4).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "measurement.schema.json"

SUPPORTED_TYPES = ("object", "array", "string", "boolean", "integer", "number")


def _type_ok(value: object, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    raise ValueError(f"unsupported JSON Schema type: {expected}")


def validate(value, schema, path="$", errors=None):
    """Validate ``value`` against draft-07 subset schema; append path-annotated errors."""
    errors = [] if errors is None else errors

    if "type" in schema:
        if schema["type"] not in SUPPORTED_TYPES:
            errors.append(f"{path}: schema uses unsupported type {schema['type']!r}")
            return errors
        if not _type_ok(value, schema["type"]):
            errors.append(
                f"{path}: type must be {schema['type']}, got {type(value).__name__}"
            )
            return errors  # deeper checks are meaningless after a type mismatch

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must be const {schema['const']!r}")

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not in enum {schema['enum']}")

    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(
                f"{path}: {value!r} does not match pattern {schema['pattern']!r}"
            )
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength={schema['minLength']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value {value} is below minimum={schema['minimum']}")

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append(
                        f"{path}: unexpected key {key!r} (additionalProperties=false)"
                    )
        for key, subschema in props.items():
            if key in value:
                validate(value[key], subschema, f"{path}.{key}", errors)

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems={schema['minItems']}")
        items = schema.get("items")
        if isinstance(items, dict):
            for idx, element in enumerate(value):
                validate(element, items, f"{path}[{idx}]", errors)

    return errors


def main(argv):
    if not argv:
        print(
            "usage: python scripts/measurement-schema/validate.py <record.json> [...]",
            file=sys.stderr,
        )
        return 1

    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL schema load ({SCHEMA_PATH}): {exc}", file=sys.stderr)
        return 1

    failed = 0
    for arg in argv:
        record_path = Path(arg).resolve()
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FAIL {record_path.name}: unreadable record ({exc})")
            failed += 1
            continue

        errors = validate(record, schema, "$")
        if errors:
            failed += 1
            print(f"FAIL {record_path.name}")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"PASS {record_path.name}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
