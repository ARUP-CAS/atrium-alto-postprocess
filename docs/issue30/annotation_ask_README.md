# Issue #30 — annotation ask

Built by `tools/build_annotation_sample.py` v1.0. Seed 30.

> ⚠️ **These files are the stage-8 delivery, and they are sized against the wrong population.
> Do not start on them.** They were built from an exposure pass run with the vocabulary lexicon
> switched off — a configuration this project does not ship (`setup/config.txt`: *"DO NOT TURN IT
> ON WITHOUT A LEXICON. These two keys are one decision."*). About **73% of the at-risk exposure
> below is already exempt** once the lexicon is configured, and the `census.csv` head is almost
> entirely made of strings the shipped configuration cannot convict. A re-cut ask is stage 9c;
> see [`issue30_annotation_guide.md`](issue30_annotation_guide.md) § 2 and
> `agent_dev_logs/digests/30.digest.md` § T1/T2. They are kept here as the delivered artefact.

Fill **`gold_categ`** only: `Clear` / `Noisy` / `Trash` / `Non-text` / `Empty`.
Leave anything uncertain **blank** — blank is skipped, never guessed.
`confidence` and `note` are free text and optional.

One row is one decision. `lines_settled` is how many lines it settles.

| file         | rows |       lines settled | what it is                                                                                                            |
|--------------|-----:|--------------------:|-----------------------------------------------------------------------------------------------------------------------|
| `census.csv` |  592 |              31,102 | The head of the at-risk population, plus every string the pipeline currently answers two ways. Complete, not sampled. |
| `sample.csv` |  200 | 9,906 (represented) | A random sample of the at-risk tail. Each row carries the weight it projects at.                                      |

## What each tranche buys

* The queue holds **50,042 strings / 100,824 lines**.
* **8,529 strings / 37,555 lines** are *at risk*: the pipeline currently keeps them, so arming the witness would newly convict them. The rest are already `Trash`, where a label cannot change the decision.
* `census.csv` settles **82.8%** of at-risk exposure in 592 decisions.
* `sample.csv` estimates the remainder to **±6.9 percentage points** (95%), from 200 decisions instead of 8,140.

**Measured against the shipped (lexicon-on) configuration, those last two lines do not hold.**
The at-risk population is **7,433 strings / 9,876 lines**, not 8,529 / 37,555; and on it the 592
census rows settle **30.7%**, not 82.8%, because the survivors average 1.33 lines per string and
93.7% of them occur exactly once. A census is the right instrument for the queue above and the
wrong one for the real population — which is why 9c re-cuts the ask as a sample rather than
re-running the same tool on a new file.

## Sampling frame — keep this file with the answers

Without it the sample cannot be projected and becomes 200 anecdotes.

| stratum           | strings | lines | sampled |  weight | 95% half-width |
|-------------------|--------:|------:|--------:|--------:|---------------:|
| `at_risk/full`    |   3,252 | 4,483 |      80 | 40.65   |       ±11.0 pp |
| `at_risk/none`    |   2,798 | 3,053 |      69 | 40.5507 |       ±11.8 pp |
| `at_risk/partial` |   2,090 | 2,370 |      51 | 40.9804 |       ±13.7 pp |

`weight` is how many tail strings each sampled row stands for. A stratum estimate is (labels of one kind ÷ rows sampled); the population estimate is the stratum estimates recombined by `lines`, not by `strings` — the strata have very different average line counts.

Note that the obvious shortcut is wrong: multiplying `lines_settled` by `sampling_weight` gives
10,051 lines against the frame's own 9,906, because the weight is a **string** weight. Use the
recombination described above.

Settings: `--census 60 --sample 200 --seed 30`.

Nothing here proposes an answer, and nothing you write changes the pipeline. The labels are joined back separately and inspected first.
