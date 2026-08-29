# Phileas conformance corpus

Language-neutral test cases that every Phileas implementation runs against its
own filter service, so the Java, Python, and .NET implementations cannot drift
apart unnoticed.

```
cases/        the corpus, one directory per filter or cross-cutting category
policies/     Phileas policy JSON, referenced by cases
schema/       JSON Schema for a case file
scripts/      the corpus validator
```

The corpus is plain data and carries no logic. Implementations do not clone this
repository: they fetch it at a pinned tag and run it after their own build
passes, so nothing in their build files refers here. The code that walks cases,
calls the filter service, and compares spans lives in each implementation,
because it has to touch that implementation's API.

Each implementation keeps its own unit tests. Those cover internals the corpus
cannot reach from the service boundary.

## Validating

```sh
pip install -r scripts/requirements.txt
python scripts/validate.py
```

Checks the case files against `schema/case.schema.json` plus the constraints a
schema cannot express, such as span offsets actually indexing the text they
claim. Runs on every push and pull request.

Whether an implementation *passes* the corpus is checked in that implementation's
own repository, not here.

## Reference

- [SCHEMA.md](SCHEMA.md) — scope, case format, determinism tiers, baselines
- [CONSUMING.md](CONSUMING.md) — what an implementation must do to run the corpus
