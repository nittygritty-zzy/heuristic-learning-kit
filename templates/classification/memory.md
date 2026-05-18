# AITL Heuristic System — memory

Maintained by the coding agent during `/aitl-update`, `/aitl-simplify`, and
`/aitl-paraphrase` runs. Mix of design rationale, failed directions, and
compression history.

The Chinese HS definition calls for memory to hold "trials, summary,
**失败原因 (failure reasons)**, replays, **版本 diff**". Trials and replays
live in JSONL files; git holds the version diff; this file holds the *why*.

## Design rationale

- `detectors.py` is separated from `policy.py` so perception (regex on the
  query) can evolve independently from response logic (what to say).
- A single detector signature: `(q: str) -> Literal[...]`. New facts about
  the query become new detector functions, not one giant `parse_query()`.
- Responses live in a `RESPONSES` dict so they can be edited without
  touching control flow.

## Failed directions (do not retry)

_none yet_

## Compression history

_none yet_
