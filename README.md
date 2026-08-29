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

## What is covered

| Type | Detects |
|---|---|
| `age` | Ages in numeric, abbreviated and spelled-out forms, and as a labelled field |
| `bank-routing-number` | US ABA routing numbers, checksum validated |
| `bitcoin-address` | Base58 Bitcoin addresses |
| `credit-card` | Card numbers for the major issuers, Luhn validated |
| `currency` | Monetary amounts by symbol or ISO code, including non-US conventions |
| `custom-dictionary` | Terms supplied inline in the policy, matched exactly or fuzzily |
| `date` | Dates in numeric, slash, dot, ISO and month-name forms |
| `drivers-license-number` | US driver's license numbers |
| `ein` | US Employer Identification Numbers |
| `email-address` | Email addresses, including the awkward but valid forms |
| `iban-code` | International Bank Account Numbers, spaced or unspaced |
| `id` | Identifiers matching a regex supplied in the policy |
| `ip-address` | IPv4 and IPv6 addresses |
| `mac-address` | MAC addresses, colon or hyphen separated |
| `passport-number` | US passport numbers |
| `phone-number` | US phone numbers, with or without punctuation and extensions |
| `phone-number-extension` | Extensions written on their own |
| `section` | Everything between a start and end marker given in the policy |
| `ssn` | US Social Security numbers, including invalid ranges that must not match |
| `state-abbreviation` | Two-letter US state abbreviations |
| `street-address` | US street addresses, with directionals and secondary units |
| `tracking-number` | UPS, USPS and FedEx shipment tracking numbers |
| `url` | URLs with and without a scheme, including IP and IPv6 hosts |
| `vin` | Vehicle Identification Numbers, check digit validated |
| `zip-code` | US ZIP and ZIP+4 codes |

Cases also cover behaviour that is not tied to one type: documents containing
several types at once, policy conditions and ignore rules, replacement
strategies, and encrypting strategies asserted by property.

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
