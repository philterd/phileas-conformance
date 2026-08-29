# Phileas conformance corpus

Language-neutral test cases that every [Phileas](https://github.com/philterd/phileas)
implementation runs against its own filter service, so the Java, Python, and .NET
implementations cannot drift apart unnoticed.

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

## Using it with other tools

Nothing about a case is specific to Phileas: each one asserts an input document
and the spans that should be found in it, by offset, type and text, which any PII
redaction tool can be measured against. What is Phileas-shaped is `policies/`,
for which another tool substitutes its own configuration, and the `filtered_text`
most cases also assert, which embeds Phileas's replacement format. Because every
case carries a `rationale` for why its expectation is correct rather than what
one implementation happens to do, the corpus reads as a specification of PII
detection rather than a description of Phileas.

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

- [SCHEMA.md](SCHEMA.md): scope, case format, determinism tiers, baselines
- [CONSUMING.md](CONSUMING.md): what an implementation must do to run the corpus

## License

Copyright 2026 Philterd, LLC.

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

"Phileas" and "Philter" are registered trademarks of Philterd, LLC.
