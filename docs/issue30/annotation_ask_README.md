# Issue #30 — annotation ask

Built by `tools/build_annotation_sample.py` v1.0. Seed 30.

Fill **`gold_categ`** only: `Clear` / `Noisy` / `Trash` / `Non-text` / `Empty`.
Leave anything uncertain **blank** — blank is skipped, never guessed.
`confidence` and `note` are free text and optional.

One row is one decision. `lines_settled` is how many lines it settles.

| file         | rows |       lines settled | what it is                                                                                                            |
|--------------|-----:|--------------------:|-----------------------------------------------------------------------------------------------------------------------|
| `census.csv` |   93 |              14,254 | The head of the at-risk population, plus every string the pipeline currently answers two ways. Complete, not sampled. |
| `sample.csv` |  200 | 1,653 (represented) | A random sample of the at-risk tail. Each row carries the weight it projects at.                                      |

## What each tranche buys

* The queue holds **4,807 strings / 20,078 lines**.
* **1,584 strings / 15,041 lines** are *at risk*: the pipeline currently keeps them, so arming the witness would newly convict them. The rest are already `Trash`, where a label cannot change the decision.
* `census.csv` settles **94.8%** of at-risk exposure in 93 decisions.
* `sample.csv` estimates the remainder to **±6.9 percentage points** (95%), from 200 decisions instead of 1,506.

## Sampling frame — keep this file with the answers

Without it the sample cannot be projected and becomes 200 anecdotes.

| stratum           | strings | lines | sampled | weight | 95% half-width |
|-------------------|--------:|------:|--------:|-------:|---------------:|
| `at_risk/full`    |     535 |   633 |      71 | 7.5352 |       ±11.6 pp |
| `at_risk/none`    |     606 |   617 |      81 | 7.4815 |       ±10.9 pp |
| `at_risk/partial` |     365 |   403 |      48 | 7.6042 |       ±14.1 pp |

`weight` is how many tail strings each sampled row stands for. A stratum estimate is (labels of one kind ÷ rows sampled); the population estimate is the stratum estimates recombined by `lines`, not by `strings` — the strata have very different average line counts.

Settings: `--census 60 --sample 200 --seed 30`.

Nothing here proposes an answer, and nothing you write changes the pipeline. The labels are joined back separately and inspected first.
