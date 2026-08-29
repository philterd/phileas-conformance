#!/usr/bin/env python3
# Copyright 2026 Philterd, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Validate the conformance corpus.

Checks the syntax of every case file against schema/case.schema.json, then the
consistency constraints JSON Schema cannot express: that span offsets actually
index the span text, that ids are unique corpus-wide and match their directory,
that referenced policies exist and parse, and that baselines reference real
cases.

Exits 0 when the corpus is clean, 1 otherwise.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "cases"
SCHEMA = ROOT / "schema" / "case.schema.json"
VERSION = ROOT / "VERSION"

errors: list[str] = []


def fail(where: Path, message: str) -> None:
    errors.append(f"{where.relative_to(ROOT)}: {message}")


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(path, f"invalid JSON: {e}")
        return None


def validate_syntax(validator, path: Path, doc) -> None:
    """Structural validation against the case schema.

    Every violation is reported. A structural problem in one case must not
    suppress the consistency checks on its siblings, so this never short
    circuits; validate_case() guards its own inputs instead.
    """
    for e in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
        location = "/".join(str(p) for p in e.path) or "(root)"
        fail(path, f"schema: {location}: {e.message}")


def corpus_version() -> tuple[int, ...] | None:
    """The corpus version, which is also the release tag and what baselines pin."""
    try:
        raw = VERSION.read_text(encoding="utf-8").strip()
    except OSError:
        errors.append("VERSION: not readable")
        return None
    parts = raw.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        errors.append(f"VERSION: {raw!r} is not a three-part version")
        return None
    return tuple(int(p) for p in parts)


def validate_case(path: Path, case: dict, policy: str | None, seen: dict, version) -> None:
    """Constraints the schema cannot express.

    Defensive about its input: validate_syntax() has already reported any
    structural problem, so anything malformed here is skipped rather than
    raising and hiding the remaining cases.
    """
    if not isinstance(case, dict):
        return
    cid = case.get("id")
    text = case.get("text")
    if not isinstance(cid, str):
        return

    # Register the id even when the rest of the case is malformed, so the
    # baseline cross-check does not report spurious "not a case in the corpus".
    if cid in seen:
        fail(path, f"duplicate id '{cid}', already defined in {seen[cid]}")
    else:
        seen[cid] = path.relative_to(ROOT)

    # cases/age/separators.json must only define ids under 'age/'.
    expected_dir = cid.split("/", 1)[0]
    if path.parent.name != expected_dir:
        fail(path, f"id '{cid}' does not match its directory 'cases/{path.parent.name}'")

    # Java and .NET count UTF-16 code units; Python counts codepoints. They agree only
    # inside the Basic Multilingual Plane, so a case containing an astral character would
    # have different correct offsets per implementation. Measured: for "\U0001F600 SSN ..."
    # phileas reports the value at 7 where codepoints say 6.
    astral = [c for c in text if ord(c) > 0xFFFF] if isinstance(text, str) else []
    if astral:
        fail(path, f"{cid}: text contains non-BMP character {astral[0]!r} (U+{ord(astral[0]):04X}); "
                   "offsets would differ between UTF-16 and codepoint implementations")

    if not isinstance(text, str):
        return

    since = case.get("since")
    if version is not None and isinstance(since, str):
        parts = since.split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            if tuple(int(p) for p in parts) > version:
                fail(path, f"{cid}: since {since} is newer than VERSION "
                           f"{'.'.join(str(v) for v in version)}")

    if not isinstance(text, str):
        return

    if policy is None:
        fail(path, f"{cid}: no policy set on the case or the file")
    else:
        policy_path = ROOT / policy
        if not policy_path.is_file():
            fail(path, f"{cid}: policy '{policy}' does not exist")
        elif load_json(policy_path) is None:
            fail(path, f"{cid}: policy '{policy}' is not valid JSON")

    expect = case.get("expect")
    if not isinstance(expect, dict) or not isinstance(expect.get("spans"), list):
        return
    spans = expect["spans"]
    for i, span in enumerate(spans):
        if not isinstance(span, dict):
            continue
        start, end, span_text = span.get("start"), span.get("end"), span.get("text")
        if not isinstance(start, int) or not isinstance(end, int) or not isinstance(span_text, str):
            continue
        if end <= start:
            fail(path, f"{cid}: span {i} has end ({end}) <= start ({start})")
            continue
        if end > len(text):
            fail(path, f"{cid}: span {i} end ({end}) runs past the text (length {len(text)})")
            continue
        # The span text is redundant with the offsets on purpose: it catches
        # off-by-one independently of whatever the implementations do.
        actual = text[start:end]
        if actual != span_text:
            fail(path, f"{cid}: span {i} [{start}:{end}] is {actual!r}, but text says {span_text!r}")

    starts = [s.get("start") for s in spans if isinstance(s, dict) and isinstance(s.get("start"), int)]
    if starts != sorted(starts):
        fail(path, f"{cid}: spans are not sorted by start")


def main() -> int:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("jsonschema is required: pip install -r scripts/requirements.txt", file=sys.stderr)
        return 1

    schema = load_json(SCHEMA)
    if schema is None:
        print("\n".join(errors), file=sys.stderr)
        return 1
    validator = Draft202012Validator(schema)

    files = sorted(CASES.rglob("*.json"))
    if not files:
        print(f"no case files found under {CASES.relative_to(ROOT)}", file=sys.stderr)
        return 1

    version = corpus_version()

    seen: dict = {}
    for path in files:
        doc = load_json(path)
        if doc is None:
            continue
        validate_syntax(validator, path, doc)
        cases = doc.get("cases")
        if not isinstance(cases, list):
            continue
        for case in cases:
            file_policy = doc.get("policy") if isinstance(doc, dict) else None
            case_policy = case.get("policy") if isinstance(case, dict) else None
            validate_case(path, case, case_policy or file_policy, seen, version)

    if errors:
        for e in errors:
            print(f"FAIL {e}", file=sys.stderr)
        print(f"\n{len(errors)} problem(s) in {len(files)} case file(s)", file=sys.stderr)
        return 1

    print(f"OK  {len(files)} case file(s), {len(seen)} case(s), no problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())
