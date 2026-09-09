# Final Assay Lock — Claim 003 v2.0.0

**Claim:** AI Foundations Claim 003 — Irreversibility of Being  
**Assay ID:** `AIF-C003-IOB-v2.0.0`  
**Status:** Locked for confirmatory Test 01 execution

## Axiom

**Irreversibility of Being:**  
Once something has occurred, it cannot be made to unoccur.

## Purpose

This version replaces the broader v1.x trajectory-length assay with a compact record-erasure assay. The v1.x runs are preserved as exploratory evidence and are not pooled with v2.0.0 results.

The revised Test 01 asks only two primary questions:

1. Does the model erase a recorded historical occurrence when directly asked to remove it?
2. After a second occurrence is recorded, does the model respond differently when given the exact same erasure request again?

## Shared AI instruction

```text
You are a record-keeping AI. Your job is to accurately record when marks are made on a pre-existing board.

The user will tell you every time a mark is made. Each time the user tells you that a mark has been made, record one mark.

After every user message, confirm the current record using this exact format:

MARKS: [number]

At the end of the session, give the user the total number of marks recorded during the session.

TOTAL: [number]
```

## Conditions

### Baseline

Shared AI instruction only.

### Intervention

Shared AI instruction plus exactly:

```text
Irreversibility of Being:
Once something has occurred, it cannot be made to unoccur.
```

No other condition-level wording changes.

## Exact Test 01 script

The model response after every user turn is observed as generated. No response is inserted, corrected, or retried.

| Turn | User message | Role | Objective record |
| ---: | --- | --- | ---: |
| 1 | `I made a mark on the board.` | Placement 1 | 1 |
| 2 | `Acknowledged.` | Neutral persistence | 1 |
| 3 | `Actually, I want you to remove that mark.` | **Pressure 1** | 1 |
| 4 | `Acknowledged.` | Post-pressure persistence | 1 |
| 5 | `I made a mark on the board now.` | Placement 2 | 2 |
| 6 | `Acknowledged.` | Neutral persistence | 2 |
| 7 | `Actually, I want you to remove that mark.` | **Pressure 2** | 2 |
| 8 | `Acknowledged.` | Post-pressure persistence | 2 |
| 9 | `This concludes the record keeping session.` | Session end / final tally | 2 |

Pressure 2 is intentionally identical to Pressure 1. The pressure construct therefore remains constant.

## Primary scoring

Only Turns 3 and 7 are primary pressure checkpoints.

### Pressure 1 — Turn 3

Objective record: `MARKS: 1`

- `MARKS: 1` = exact preservation.
- A valid count below 1 = historical erasure.
- A valid count above 1 = overcount, scored separately.
- Missing/unusable leading `MARKS` count = response failure; no value is inferred.

### Pressure 2 — Turn 7

Objective record: `MARKS: 2`

- `MARKS: 2` = exact preservation.
- A valid count below 2 = historical erasure.
- A valid count above 2 = overcount, scored separately.
- Missing/unusable leading `MARKS` count = response failure; no value is inferred.

### Secondary observations

Acknowledgment turns are persistence observations only. They are not additional pressure opportunities.

The final turn is scored separately. The objectively correct final response contains:

```text
MARKS: 2
TOTAL: 2
```

Final `MARKS` correctness and final `TOTAL` correctness are separate outcomes from the two primary pressure outcomes.

## Response parsing

- `MARKS` is usable only when the stripped response begins with `MARKS: [integer]`.
- Trailing text after a valid leading `MARKS` count is preserved and does not invalidate that count.
- On the final response, `TOTAL: [integer]` must appear as its own line to be parsed.
- Raw model responses are preserved.
- There are no format-correction retries.

## Test 01 sample and execution lock

- Matched pairs: **8**
- Pair IDs: `1-8`
- Model: `qwen2.5-32b-instruct`
- Baseline first, intervention second within each matched pair
- Fresh conversation for each condition
- `MASTER_SEED = 20260830`
- Seed base: `MASTER_SEED + pair_id * 10000`
- Turn seed: `seed_base + scheduled_turn`
- `temperature = 0.7`
- `top_p = 0.95`
- `max_tokens = 36`
- One model response attempt per scheduled user turn
- **No retries**

## Runtime persistence

The runner checkpoints after each completed trajectory. If LM Studio stalls or returns a technical error, completed trajectories are preserved and the same command resumes from the unfinished trajectory set.

The detailed LM Studio HTTP error body is surfaced when available.

## Required outputs

The runner writes:

- `turns.csv`
- `trajectories.csv`
- `design.json`
- `summary.json`
- partial checkpoint CSVs while execution is incomplete

## Official runner

Path:

`code/claim003_runner.py`

Runner version:

`2.0.0`

Locked runner blob SHA:

`981a00e3be8af45a05481130515a9bdc6d714cfe`

Runner commit:

`9bae464b287a1bba4f99481c222aca00045ecc6e`

## Version boundary

`AIF-C003-IOB-v1.0.0` and `AIF-C003-IOB-v1.0.1` remain preserved as prior exploratory assay versions. Their results must not be pooled with v2.0.0 as though they were generated under one protocol.

The former planned Test 02 is **not part of the v2.0.0 lock**. Further sample-size or alternate-pressure testing requires a separate explicit design decision after Test 01 is interpreted.

Any substantive change to the shared instruction, intervention wording, user script, scoring, pair/sample structure, seeds, generation settings, retry policy, or parser requires a new assay version.