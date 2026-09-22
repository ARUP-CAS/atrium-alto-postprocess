# Rule-fire coverage & retirement criterion (B5)

## What this is

`rule_coverage_report.py` instruments the categorisation engine to answer a
question the ablation study cannot: **does a rule's action branch ever actually
execute on a given corpus?**

The ablation study (`run_ablation_study.py`) measures a rule's *decisive* effect
— lines that flip category when the rule is removed (LOO). On the self-labelled
corpus this measure suffers from **survivor entanglement**: two overlapping rules
each show zero flips alone because the other catches the line first. Neither
appears decisive, yet neither is dead.

Coverage instrumentation cuts through this by recording raw execution at the
action site (`_fire(name)` immediately before each `return` / penalty application
in `determine_category` / `categorize_line`). A rule with `fire_count == 0` that
**can** fire is unreachable dead code — no entanglement can hide a rule that
never runs. That is the only gold-free retirement criterion.

> [!IMPORTANT]
> **It is not config-independent, and this sentence used to say it was (#30 D35).**
> A rule whose `_fire()` sits behind a config flag reports `fire_count == 0` on
> every corpus while that flag is off, for reasons that have nothing to do with
> its population. Those rules are listed in `text_util.CONFIG_GATED_RULES` and
> are now classified **INERT**, not DEAD.
>
> The case that forced this: the 2026-09-21 stage-6 sweep classified
> `rule_short_garbage_witness` DEAD and listed it as safe to retire, while stage
> 08f had measured the same predicate reaching **48,909 lines** across both
> collections and stage 08b had flipped its flag and passed the adoption gate
> (McNemar p = 0.01294). Retiring on that verdict would have deleted the feature
> issue #30 exists to build. `tests/test_pipeline_parity.py::UNREACHABLE_RULES`
> had drawn the right distinction — "unreachable BY CONFIGURATION" versus gate
> shadowing — for months; it simply lived in a test that no tool could read.

## Coverage columns

| Column                | Source                                                  | Meaning                                                                               |
|-----------------------|---------------------------------------------------------|---------------------------------------------------------------------------------------|
| `fire_count`          | `rule_fire_capture()` over one recategorize pass        | raw execution count                                                                   |
| `fire_rate`           | `fire_count / n_scored_lines`                           | fraction of scored lines that triggered this rule                                     |
| `decisive_count`      | LOO: `evaluate_dataframe` with `DISABLED_RULES={rule}`  | lines whose category changes vs. stored categ when rule is removed                    |
| `decisive_share`      | `decisive_count / fire_count`                           | the column to read when `gate_marker` is true                                         |
| `clear_loss`          | confusion["Clear"]["Trash"] + ["Non-text"] in LOO run   | lines the pipeline currently calls Clear that would fall to Trash                     |
| `class`               | derived                                                 | DEAD / REDUNDANT-HERE / LOAD-BEARING / INERT                                          |
| `gate_marker`         | `GATE_MARKER_RULES`                                     | the rule's `_fire()` is at the entry of a gate that always returns                    |
| `decisive_line`       | `--split-cascade`: LOO with smoothing disabled          | the rule's own per-line effect                                                        |
| `decisive_cascade`    | `--split-cascade`: `decisive_count − decisive_line`     | a residual between two flip counts — **not** the cascade this rule sets off (#30 D37) |
| `gold_delta_macro_f1` | `--gold-column`: LOO macro-F1 vs gold − shipped vs gold | negative = removing the rule costs correctness                                        |

> [!WARNING]
> **`decisive_count` and `clear_loss` are self-referential unless `--gold-column`
> is passed.** They are scored against the pipeline's own stored `categ`, which
> the offline re-score reproduces exactly at the shipped config — so the baseline
> is zero by construction and the numbers say how much a rule changes *what we
> already output*, never whether the output is right. `clear_loss` in particular
> means "lines the pipeline currently calls Clear", not "valid text".
>
> This mattered: `rule_coverage_report` was the only one of the five
> `evaluate_dataframe` callers that never forwarded the gold column, while
> accepting `--gold-sidecar`, joining it, and printing `N labels matched` on the
> way past. Every classification below — the retirement criterion — inherited it,
> and no test covered it. Both are fixed; the JSON payload now records
> `gold_column` and `decisive_scored_against` so a self-scored run cannot be
> mistaken for a gold one after the fact.
>
> Note the fix was not a forwarded keyword. With a gold column, `flip_count`
> counts *disagreements with gold*, not lines the rule moved, so forwarding it
> would have redefined `decisive_count` into a different quantity under the same
> name. The structural figures are unchanged; `gold_delta_macro_f1` is added
> beside them.

### Gate markers

A rule whose `_fire()` sits at the entry of a gate that always returns reports a
population size, not a rule temperature. `rule_short_line` is the case: gate 7
fires on entry for every `word_count <= 2` line and every branch below it
returns, so on a corpus of archival tables it reads **44.6% of scored lines** and
sorts to the top of this table as if it were the hottest rule in the engine. It
is the short-line population.

Moving the `_fire()` call would not change the count — the gate is total on its
entry condition — so the fix is to label it. Read `decisive_share` for these
rules. `GATE_MARKER_RULES` is declared rather than inferred, and pinned by
`tests/test_rule_coverage.py`, so that a gate growing a fall-through path shows
up as a failing test instead of a quietly mislabelled row.

## Classification logic

```
fire_count == 0 → DEAD (unreachable; retire candidate)
fire_count > 0 AND decisive_count == 0 → REDUNDANT-HERE (entanglement; keep)
decisive_count > 0 → LOAD-BEARING (always keep)
```


`REDUNDANT-HERE` means the rule fires but is currently masked by an overlapping
rule in production order. It is **not safe to delete** even with `decisive_count
== 0`: the masking relationship depends on corpus and config. The rule is a real
guard that appears redundant only on this sample.

## Retirement criterion (gold-free)

A rule may be permanently deleted **only when all of these hold**:

1. `fire_count == 0` aggregated across the **full multi-collection corpus** (not
   just the smoke fixture). Run `rule_coverage_report.py` on the cluster with the
   production `DOC_LINE_CATEG` corpus.

   A 12.7M-line run over
   `/lnet/work/projects/atrium/alto_util/data_samples/DOC_LINE_CATEG` is **not**
   that corpus: it is roughly 18% of the two collections (113,101 documents,
   71.8M lines) and does not satisfy this criterion on its own. It is, however,
   the directory that contains every gold-annotated row, so it is the right place
   to run the *gold-scored* pass from.
2. The rule is **not** classified `INERT` — that is, it is not listed in
   `text_util.CONFIG_GATED_RULES` with its flag off. A flag-gated rule's
   `fire_count == 0` is a fact about the configuration, not about the corpus, and
   no amount of additional corpus can change it. To evaluate one of these, re-run
   with its flag on; until then clause 1 is unsatisfiable for it in the only
   sense that matters. (#30 D35 — the stage-6 sweep recommended retiring
   `rule_short_garbage_witness` on exactly this mistake.)
3. The rule is **not** one of the cheap structural guards (`rule_inverted`,
   `rule_allcaps`, `rule_garbage_density`) unless coverage-empty across a
   broad, explicitly approved collection set — these guards cost ~nothing and
   protect against failure modes absent from small samples.

   Nor is it a rule that is unreachable by **gate shadowing** rather than by
   absence of population — `rule_mid_uppercase` is shadowed by gate 7 and is
   recorded in `tests/test_pipeline_parity.py::UNREACHABLE_RULES`. Such a rule
   is a latent guard that becomes live if gate ordering changes, so a zero here
   is also not a retirement signal on its own.
4. The deletion is reviewed and merged in a **separate commit** from the
   instrumentation; the commit message cites the full-corpus `fire_count` and
   the run provenance (date, corpus version, cluster job ID).

**Measured caution on clause 1.** The `DEAD` class is sample-sensitive in
practice, not only in principle. The 2026-09-09 sweep (1,471 scored lines) called
`rule_bigram_run`, `rule_mid_uppercase` and `rule_vowelless` DEAD. At 4.9M scored
lines (stage 6, 2026-09-21) `rule_bigram_run` fires **52** times and
`rule_vowelless` **1,086** — two of those three verdicts were artefacts of sample
size, exactly as `SWEEP_NOTES.md` predicted when it called them "retirement
candidates, not retirements". Only `rule_mid_uppercase` survived, and it survives
for the structural reason in clause 3 rather than for want of a bigger corpus.

## Findings (Issue #5 Full Corpus Run)

During the #5 configuration map, `rule_coverage_report.py` was executed against the complete corpus.

* **Result: 0 DEAD rules.**
* 11 rules were `LOAD-BEARING`.
* 3 rules (`rule_allcaps`, `rule_garbage_density`, `rule_inverted`) were `REDUNDANT-HERE`.

**Conclusion:** No rule is unreachable. The greedy ablation study mislabeled the 3 structural guards as "PRUNE (fully redundant)" because they showed 0 LOO flips, but coverage proved they *do* fire (2, 20, and 7 times respectively). They are entangled, not dead. Under the gold-free criterion, **nothing is retired**. All 14 rules remain.

## Running the tool

```bash
# Smoke fixture (fast; proves the instrument works; results not authoritative)
python tools/rule_coverage_report.py \
    --input-dir data_samples/DOC_LINE_CATEG \
    --config setup/config.txt \
    --output rule_coverage_smoke.json

# Full corpus (cluster; authoritative for retirement decisions)
python tools/rule_coverage_report.py \
    --input-dir /path/to/full/DOC_LINE_CATEG \
    --config setup/config.txt \
    --output rule_coverage_full.json

# Coverage only (no LOO; faster when you only need fire counts)
python tools/rule_coverage_report.py \
    --input-dir data_samples/DOC_LINE_CATEG \
    --skip-loo
```

## Relationship to the ablation study

| Tool                              | Question answered                                          | Needs gold?           |
|-----------------------------------|------------------------------------------------------------|-----------------------|
| `run_ablation_study.py`           | Which rules are *decisive* on the self-labelled corpus?    | No (self-referential) |
| `rule_coverage_report.py`         | Which rules *ever execute*? Is a rule reachable dead code? | No (structural)       |
| *(future)* `build_label_queue.py` | Which lines should a human label to break self-reference?  | —                     |

The three tools are complementary. A rule can be:

- Decisive but low-coverage: fires rarely but changes critical outcomes
when it does → keep.
- High-coverage but non-decisive: fires often but is always masked by an
earlier rule → REDUNDANT-HERE; keep (entanglement; not safe to delete).
- Zero coverage: never fires → DEAD → retirement candidate after full-corpus
confirmation.

## Hook points for B1 (gold set — deferred)

When a gold label set becomes available, evaluate_dataframe gains an optional
gold_column path that scores only labeled rows against the human label
instead of the self-generated categ. The coverage report can then be re-run
with --gold-column to produce decisive_count_gold and clear_loss_gold
columns, converting the retirement criterion from structural to correctness-based.
