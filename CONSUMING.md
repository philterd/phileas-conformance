# Running the corpus against an implementation

This is the integration contract. With no package to declare, it is the only
place the contract is written down.

## What an implementation has to provide

**A conformance stage that runs after the build passes.** Not part of the normal
unit test run. A red unit test means the implementation is broken; a red
conformance stage means it has drifted from the corpus. Keep them separable.

**A loader** that reads the corpus and drives the implementation's plain-text
filter service. It lives in the implementation's repository, because it has to
call that implementation's API. It must:

1. resolve the corpus root: an explicit local checkout wins, otherwise fetch the
   pinned ref from GitHub and cache it under the build directory. A value that
   does not hold a corpus is an error; nothing set at all means do not run;
2. read `<root>/VERSION` and fail if it does not match `corpus_version` in the
   implementation's own baseline;
3. walk `<root>/cases/**/*.json`, resolving each case's `policy` relative to
   `<root>`;
4. for each case, deserialize the policy, call the filter service with the case
   text, and compare the applied spans (`start`, `end`, `type`, `text`) against
   `expect.spans`, exhaustively and in order;
5. compare `filtered_text` when the case declares it;
6. check `expect.properties` when the case declares them, for strategies whose
   exact output is not reproducible (see SCHEMA.md);
7. apply the baseline rules below.

**A baseline file** listing the cases it does not yet pass.

## The baseline rules

| situation | outcome |
|---|---|
| case fails, not in the baseline | fail the build |
| case fails, listed in the baseline | report it, do not fail |
| case passes, listed in the baseline | **fail the build** |

The third rule is the one that matters. Without it the baseline silently rots as
filters improve, and the gap it describes stops being true.

## Per-implementation wiring

| implementation | corpus location | baseline |
|---|---|---|
| `philterd/phileas` | `-Dconformance.dir=<root>` | `src/test/resources/conformance-baseline.json` |
| `philterd/phileas-python` | `PHILEAS_CONFORMANCE_DIR=<root>` | `tests/conformance-baseline.json` |
| `philterd/phileas-dotnet` | `PHILEAS_CONFORMANCE_DIR=<root>` | `tests/Phileas.Tests/Resources/conformance-baseline.json` |

`<root>` is the corpus root, not `cases/`: case files reference their policy
relative to the root.

## Pinning a version

`VERSION` holds the corpus version, which is also the release tag (`v0.1.0`) and
the value each implementation records as `corpus_version` in its baseline. One
number across all four repositories, so "phileas passes corpus 0.1.0" compares
directly between implementations.

The pin lives in the implementation's own build file, not in CI config, so it
appears once:

```xml
<conformance.ref>v0.1.0</conformance.ref>
```

A commit SHA is accepted and is the stronger pin, since a tag can be moved.
Because the ref is pinned, a case added here reaches an implementation only when
that implementation moves its pin.

## Iterating locally

Point at a checkout to run a case against a filter you are changing, without
tagging or publishing anything:

```sh
mvn verify -Pconformance -Dconformance.dir=../phileas-conformance
PHILEAS_CONFORMANCE_DIR=../phileas-conformance pytest
PHILEAS_CONFORMANCE_DIR=../phileas-conformance dotnet test
```

The path is the corpus root, not `cases/`, because cases reference their policy
relative to the root.

## CI shape

```yaml
- name: Build and unit test
  run: mvn --batch-mode package

- name: Conformance
  run: mvn --batch-mode verify -Pconformance
```

No checkout step: the corpus is fetched from GitHub at the ref pinned in the
implementation's own build file, so the pin lives in one place rather than being
repeated in CI configuration where it can drift.

Pinning is what keeps this repository from breaking anyone. A case added here
reaches an implementation only when that implementation moves its pin, and that
move plus either the fix or a new baseline entry is one pull request in one
repository.

## Adding a case

1. Add it here with a `rationale` saying why the behavior is correct. Not what one
   implementation happens to do. A case may assert behaviour no implementation
   has yet; it stays a baseline entry, against an issue, until one does.
2. Run `python scripts/validate.py`.
3. Iterate against a local checkout, which overrides the fetched copy:
   `mvn verify -Pconformance -Dconformance.dir=../phileas-conformance`.
4. Merge here and tag.
5. In each implementation, bump the pin and either fix the filter or add a
   baseline entry with an issue link.

Steps 4 and 5 are separate pull requests, but neither blocks the other: the
implementations are pinned to the old tag until they choose to move.
