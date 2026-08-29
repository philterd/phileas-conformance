# Case format and consumption

Status: draft for review.

## Scope

Rules-based filters: regex, validator, and dictionaries whose terms are supplied
inline in the policy. Out of scope:

- **Model-backed filters** (PhEye), whose output moves with model versions.
- **Filters backed by a bundled dictionary** (first name, surname, city, county,
  state, hospital). A case like "Fayette is a county" asserts the contents of a
  shipped word list, not filter behaviour, and each implementation ships its own.
  Phileas makes this concrete: its test resources include fixture copies of
  `surnames.txt` and friends that shadow the production lists, so the same policy
  and input give different spans depending on the classpath. Custom dictionaries
  are in scope precisely because the case carries its own terms.
- **Filters that exist in only one implementation** (physician name), which
  cannot be a parity claim.

## Binding point

Cases bind to each implementation's plain-text filter service, not to individual
filter classes, whose constructors differ too much to share cases across.

| | call | spans |
|---|---|---|
| Java | `PlainTextFilterService.filter(policy, context, input)` | `getExplanation().appliedSpans()` |
| Python | `FilterService.filter(policy, context, document_id, text)` | `.spans` |
| .NET | `FilterService.Filter(...)` returning `TextFilterResult` | `.Spans` |

The signatures are close but not identical. Java takes no document id at this
layer, so the corpus does not carry one. Java splits applied from identified
spans while the other two return a single list, so the corpus asserts one list
and the Java loader uses `appliedSpans()`, which matches the others.

All three deserialize the same Policy JSON, so `policies/*.json` are consumed
unmodified by each. That shared policy schema is what makes the corpus possible.

## Case file

A file groups cases that share a policy.

```json
{
  "schema": 1,
  "policy": "policies/age-redact.json",
  "tags": [
    "regex",
    "age"
  ],
  "cases": [
    {
      "id": "age/separator-colon",
      "text": "Patient age: 55 presented today.",
      "expect": {
        "spans": [
          {
            "start": 8,
            "end": 15,
            "type": "age",
            "text": "age: 55"
          }
        ]
      },
      "rationale": [
        "'age:' with a colon separator is a common EHR field label, so it is age data and must be redacted.",
        "No implementation detects it today: phileas accepts only whitespace between the keyword and the value. See philterd/phileas#332."
      ],
      "since": "0.1.0"
    }
  ]
}
```

### Fields

| field | required | notes |
|---|---|---|
| `id` | yes | Globally unique and permanently stable. Baselines reference it. Never renumber or rename, retire instead. |
| `text` | yes | The input document. |
| `policy` | file or case | Path to a policy JSON, relative to the corpus root. |
| `expect.spans` | yes | Exhaustive, sorted by `start`. |
| `expect.filtered_text` | no | Only for deterministic strategies (see below). |
| `rationale` | yes | Why this is correct behavior, not what one implementation happens to do. |
| `since` | yes | Corpus version that introduced the case. |
| `tags` | no | Descriptive only; no tooling selects on them yet. |

### Span object

Mirrors the `Span` model, which is already near-identical in all three
implementations (`character_start`, `character_end`, `filter_type`, `text`,
`replacement`, `ignored`, `applied`).

| field | required | notes |
|---|---|---|
| `start` | yes | Character offset, half-open `[start, end)`. |
| `end` | yes | |
| `type` | yes | Canonical wire name from `FilterType`: `age`, `ssn`, `email-address`, `drivers-license-number`, `id`, and so on. Not the Java enum constant. |
| `text` | yes | The matched substring. Redundant with the offsets by design: it makes failure diffs readable and catches off-by-one independently. |

`expect.spans` is exhaustive on purpose. Roughly half the parity problem is
over-detection, and a "contains" assertion would never catch it.

There is no `confidence` field, and no per-case `context`. Both were drafted and
then dropped: nothing asserted them, so they would have been fields a case author
could set and silently have ignored. Add them back alongside a loader that
honours them, not before.

There is no `ignored` field. A span suppressed by the policy's `ignored` or
`ignoredPatterns` is dropped rather than applied, so it never reaches the applied
span list the corpus binds to. Cases covering ignore rules assert an empty span
list plus an unchanged `filtered_text`, which is the observable contract.

## Determinism tiers

Detection is always asserted. Replacement is asserted only where reproducible,
via `expect.filtered_text`, which every implementation exposes
(`getFilteredText()`, `.filtered_text`, `.FilteredText`).

Deterministic, may be asserted: `REDACT`, `MASK`, `STATIC_REPLACE`, `TRUNCATE`,
`TRUNCATE_TO_YEAR`, `ABBREVIATE`, `LAST_4`, `SHIFT`, `RELATIVE`.

Not asserted as exact text: `RANDOM_REPLACE` and `MAP_REPLACE`, which are not
reproducible at all.

**Encrypting strategies are asserted by property instead.** Measured against
phileas: `CRYPTO_REPLACE` produces different ciphertext on every call, even for
the same value in the same document with a pinned key and IV, so no exact
assertion is possible even within one implementation. `FPE_ENCRYPT_REPLACE` is
deterministic and format preserving, but whether two implementations produce the
same ciphertext depends on their FF3 parameters, which is a portability question
the corpus should not prejudge.

So a case may carry `expect.properties` instead of `expect.filtered_text`.
Detection is still asserted exactly; only the replacement text is described by
property:

| property | meaning |
|---|---|
| `original-absent` | no matched value survives anywhere in the output |
| `replacement-differs` | every replacement differs from the value it replaced |
| `format-preserved` | each replacement has the same length and the same character-class shape, digit for digit and letter for letter, with other characters unchanged in place |
| `consistent-within-document` | equal values receive equal replacements |
| `distinct-values-differ` | different values receive different replacements |

`original-absent` is the safety-critical one: it holds for every encrypting
strategy and is the property a redaction tool cannot be allowed to break.

## Baselines

The corpus is retrofitted onto implementations that already disagree, so it will
not pass everywhere on day one. A baseline records which cases one implementation
does not yet pass.

**A baseline lives in the implementation it describes, not here**, because it
describes that implementation's current state rather than the corpus. Keeping
them here would make a contributor who fixes a filter open a second pull request
against this repository just to delete a line about the one they fixed.

```json
{
  "schema": 1,
  "implementation": "phileas-python",
  "corpus_version": "0.1.0",
  "known_failures": [
    {
      "id": "age/word-form-hyphenated",
      "reason": "not-implemented",
      "issue": "https://github.com/philterd/phileas-python/issues/123",
      "note": "AgeFilter has no NUMBER_WORD pattern."
    }
  ]
}
```

`reason` is one of `not-implemented`, `divergent-behavior`, `wontfix`; `issue` is
required for the first two. A filter an implementation does not have yet is an
ordinary `not-implemented` entry rather than a separate skip mechanism, so the
gap stays visible.

See [CONSUMING.md](CONSUMING.md) for the rules a loader applies to these entries
and where each implementation keeps its file.
