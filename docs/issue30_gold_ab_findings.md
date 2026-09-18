# Issue #30 — findings from the gold-scored parameter runs

*Analysis date 2026-09-18. Sources: the stage 1–5 logs of the issue-30 runbook job, the
two non-log artefacts (`token_df.tsv`, `04_witness_candidates.csv`), and
`ufal/atrium-alto-postprocess` at `test` HEAD `b8a38f6`. Every figure below that is not
quoted from a log was recomputed from those artefacts against the committed predicate.*

---

## 0. Provenance, before anything else

Two checks first, because several conclusions below contradict things currently written
in the repository and in the issue thread.

**The candidate file was produced by the committed code.** All 20,324 rows of
`04_witness_candidates.csv` reproduce exactly when `text_util.shape_garbage_clauses()` at
`b8a38f6` is re-run over their text — 20,324/20,324, zero clause-string differences. The
run measured what the tree contains.

**The A/B logs did not.** They were produced by an older `tools/ab_constant_eval.py`.
Since then that tool has gained an `errors` column, `mcnemar_exact()`, and an adoption
gate built on errors/cost/Clear-loss rather than `macro_f1`. Any log whose table has no
`errors` column predates that upgrade, and every stage-5 log in hand is one. **Re-running
stage 5 on a current checkout is not a formality — the verdict lines change.**

---

## 1. The gold set is smaller than it looks, in the way that matters

`01_preflight.log` is good news and was read as better news than it is: 2,064 of 2,067
sidecar keys join, no document absent, three locator drifts. All three drifted keys are
annotated `Clear`, so the joined class supports are exact:

| gold label |    rows |    share |
|------------|--------:|---------:|
| Clear      |   1,305 |    63.1% |
| Noisy      |     332 |    16.1% |
| Empty      |     205 |     9.9% |
| **Trash**  | **180** | **8.7%** |
| Non-text   |      45 |     2.2% |

That 180 is the denominator of every `Trash-recall` figure in the stage-5 logs, and **the
logs never print it.** `0.1222` is 22/180. It is also exactly 11/90, and nothing in the
output distinguishes them. This is not a hypothetical hazard: reconstructing the paired
counts from the recall deltas on the smaller denominator halves `b` and turns an exact
McNemar p of 0.004 into 0.18 — "underpowered, do not quote it" for a result significant at
the 0.01 level. One printed integer prevents it, and §7 adds it.

**The number that actually bounds this decision is smaller still.** Of the 20,324 lines
the witness fires on, **25 carry a gold label — 0.12%.** The witness cannot change the
category of a line it does not fire on, so every macro_f1 delta, every Clear-loss figure
and every adopt/reject verdict in stages 5a–5c is computed off those 25 rows plus whatever
the page cascade moves downstream of them. Document coverage is not the problem (453 of
the 457 witness-touched documents are gold documents); *line* coverage is.

Here is the whole decision surface:

| gold      | current `categ` | effect of arming the witness | text                                            |
|-----------|-----------------|------------------------------|-------------------------------------------------|
| Trash     | Clear           | fixes                        | `utlll`                                         |
| Trash     | Clear           | fixes                        | `deutendes. Alhimiaal`                          |
| Trash     | Clear           | fixes                        | `mpsssssdym"" ! IU`                             |
| Trash     | Noisy           | fixes                        | `NWIIIIIIIIIIII`                                |
| Trash     | Clear           | fixes                        | `ymeememe, mieme?`                              |
| Trash     | Clear           | fixes                        | `sektlll`                                       |
| Trash     | Noisy           | fixes                        | `SEEEEEEEEEEEE:`                                |
| Trash     | Clear           | fixes                        | `vdoaotacth.`                                   |
| Trash     | Noisy           | fixes                        | `MI*I\ EOOCO`                                   |
| Trash     | Clear           | fixes                        | `IAALAILIL`                                     |
| Trash     | Clear           | fixes                        | `LLRIOAILCIIL\`                                 |
| Trash     | Noisy           | fixes                        | `HHCCJCJ`                                       |
| Trash     | Clear           | fixes                        | `tirrttitt`                                     |
| Trash     | Clear           | fixes                        | `NINNNIC`                                       |
| Trash     | Clear           | fixes                        | `cuxoaid ,`                                     |
| Trash     | Clear           | fixes                        | `cuxoaid ,` *(second locator)*                  |
| **Clear** | **Clear**       | **breaks**                   | `Frauenzimmerbad", sämtlic Gesellschastsbäder,` |
| **Clear** | **Clear**       | **breaks**                   | `S-VIIIb`                                       |
| Noisy     | Noisy           | breaks                       | `Poue`                                          |
| Noisy     | Noisy           | breaks                       | `Lokolieace: •VIII,`                            |
| Noisy     | Clear           | wrong before, wrong after    | `Iokalisqce: HVIII,`                            |
| Non-text  | Noisy           | wrong before, wrong after    | `IDIDIDIDIDIDUOID`                              |
| Noisy     | Trash           | already Trash                | `kmixxxx`                                       |
| Clear     | Trash           | already Trash                | `http://www.arub.cz` ×2                         |

16 fixes, 4 breaks. The reported deltas — Trash-recall 22→36 (+14), Clear-loss 40→42 (+2)
— are the same rows after the full stack, including the signal half of gate 5 and document
post-processing, has had its say.

---

## 2. The witness works, and it is significant

| arm | macro_f1 | Trash-recall | Clear-loss | verdict |
|---|---:|---:|---:|---|
| shipped (witness off) | 0.6173 | 22/180 = 12.2% | 40 | incumbent |
| **5a — witness on, no lexicon** | **0.6366** | **36/180 = 20.0%** | 42 | best arm |
| 5a-bis — witness on + vocabulary veto | 0.6338 | 34/180 = 18.9% | 42 | worse on every column |
| 5b — vowel-run 4 instead of 3 | 0.6319 | 32/180 = 17.8% | 42 | strictly worse |
| 5c — + unattested-token conviction | 0.6570 | 78/180 = 43.3% | **63** | best macro_f1, worst cost |

Exact two-sided McNemar for 5a against the shipped labels:

* from the reported deltas (b = 14, c = 2): **p = 0.0042**
* from the enumerated surface above (b = 16, c = 4): **p = 0.0118**

Either way this is a real effect, not a coin-flip. Wilson 95% intervals on Trash-recall:
22/180 = 12.2% [8.2, 17.8] against 36/180 = 20.0% [14.8, 26.4] — the intervals do overlap,
which is exactly why the *paired* test is the right one and the two marginal rates are not.

**So the correct reading of stage 5a is not "promising but underpowered". It is "a
statistically significant improvement that fails the adoption gate on two identified
lines".** Those two lines are §4.

---

## 3. The vocabulary veto is not a precondition — and `ppole` is why the old figure said it was

`setup/config.txt` currently states, in capitals, *"AND DO NOT TURN IT ON WITHOUT A
LEXICON. These two keys are one decision."* The 2026-09-17 comment gives the reasoning: the
witness alone confirms 5,107 Trash verdicts and newly convicts 15,217 Clear/Noisy lines
("1:3 against"); with the veto, 3,905 against 2,306 ("1.7:1 in favour"), *"an 85% cut in
false-positive exposure for 24% of the confirmations"*.

Both ratios are scored against `categ` — the answer the pipeline already gave — and both
are one string:

* the `ppole` family is **11,685 of those 15,217** false-positive candidates (**76.8%**);
* of the 12,911 lines the veto rescued, **11,685 (90.5%) are `ppole`**.

`ppole` is attested at document frequency 35 because a pre-printed form repeats the same
misread once per document. It de-geminates to `pole` at df 163 — a ratio of 4.66. It is
damaged text. **The veto's headline benefit was protecting garbage**, and the shipped
`SHORT_GARBAGE_LEXICON_GEMINATE_RATIO = 4.0` guard is what stopped it between the 09-17
exposure run and the 09-18 gold run.

Against gold, with that guard in place, the veto's entire measured effect is to give back
**two true Trash catches — both the line `cuxoaid ,`** — because `cuxoaid` reaches df 4.
It returns **zero** Clear lines: Clear-loss is 42 with the veto and 42 without.

Set `ppole` aside and the shape witness needs no lexicon at all to look reasonable:

| | lines | Trash confirms | new Clear/Noisy convictions | ratio |
|---|---:|---:|---:|---|
| all witnessed | 20,324 | 5,107 | 15,217 | 1:3 against |
| minus the `ppole` family | 8,634 | 5,102 | 3,532 | **1.44:1 in favour** |

The same string distorts the per-clause table. `initial_geminate` reads as a disaster —
94.6% of its fires are currently Clear — and is 31.6% non-Trash once `ppole` is removed,
in line with `vowel_run` (33.6%) and better behaved than `low_variety` (41.5%).

### The self-corpus lexicon has the wrong axis, and more documents will not fix it

The 09-17 next step was *"rebuild the lexicon over both full collections"* to set the
threshold. That will not separate these populations, because the confusion is not sparsity:

| token             | df at 822 docs | what it is                                              |
|-------------------|---------------:|---------------------------------------------------------|
| `ppole`           |             35 | OCR doubling of `pole` — **attested garbage**           |
| `cuxoaid`         |              4 | garbage — **attested**, and it costs a gold-Trash catch |
| `okraie`          |              3 | OCR of `okraje` — **attested garbage**                  |
| `Naiade`          |              0 | real term — **unattested**                              |
| `Skelettmaterial` |              2 | real term — **unattested**                              |

A *systematic* OCR error recurs across scans exactly as a word does, so document frequency
cannot tell them apart, and scaling from 822 to 113,101 documents raises every artefact's
df at least as fast as it raises a rare real term's. The de-gemination guard is the right
*shape* of answer — it asks whether a **repair** of the token is attested, not whether the
token is — and that generalises where a threshold does not.

Two corrections to that guard's own documentation, from re-measuring it on the same table.
Its load-bearing claim is exactly right: **8 tokens at or above 4× — `ppole`, `oobjekt`,
`jjámy`, `ssuti`, `vvkop`, `ssutí`, `ssutě`, `llocm` — with a genuinely empty gap from
2.60× to 4.66×.** But "36 below 2×" is 51 when both forms must be attested at `MIN_DF`, and
66 when the twin is counted at any frequency; 36 matches neither filter. And on this corpus
the guard's entire reach is one family: of the 11,690 lines where it restores a conviction,
all 11,690 are `ppole` and its 17 surface forms. It currently does exactly one job. Stage
5d (added to the runbook) measures whether that job is worth its place.

---

## 4. The two lines blocking the flag, and what closes them

Clear-loss 40 → 42 is the only thing standing between stage 5a and `ADOPT-CANDIDATE`. Both
lines are identified, and each is a narrow defect rather than a policy question.

**`Frauenzimmerbad", sämtlic Gesellschastsbäder,` — gold `Clear`.** The witness's
line-level diacritic veto is `has_cz_diacs()`, Czech only, while `EXPECTED_LANGS` is
`ces,deu,eng` and `DEU_DIACS` has been in the config since the #7 Tier-1 pass. German is
where the vowel-run clause is least safe — `Frauen`, `Bauern`, `Feuer`, `Neue` are all
three-vowel runs in ordinary words — and this line reaches the clauses with no diacritic
veto at all despite carrying `ä` twice.

*Corpus scale:* 239 witnessed lines (1.18%) carry a German diacritic — 156 currently
Clear/Noisy (`Grauer, geschlämmter Ton.` and its family, readable German pottery
description), 83 currently Trash.

**`S-VIIIb` — gold `Clear`.** `is_domain_notation('S-VIII-b')` returns `True`;
`is_domain_notation('S-VIIIb')` returns `False`. The two differ by one hyphen. The corpus
carries the whole series from one excavation — `AA-VIIIb`, `E-VIIIb`, `F-VIIIb`, `J-VIIIb`,
`K-VIIIc`, `L-VIIIb`, `S-VIIIb` — 7 lines, 6 of them currently Clear.

Both now have **witness-local** guards in `text_util.py` (§7). Witness-local, not a
widening of `is_domain_notation()`, because that predicate is also read by
`rule_short_garbage`'s outer guard and the two perplexity-only routes: changing it there
would move production behaviour while the flag is still false. Inside the predicate the
change cannot do anything until the flag flips — the same discipline the existing
roman-numeral and taxonomy exemptions follow.

Measured on the gold surface, the two guards veto **exactly** the two gold-`Clear` lines
and **none** of the 16 gold-`Trash` catches. Corpus-wide they trade 84 Trash confirmations
for 162 false-positive candidates (20,324 → 20,078 lines; 5,243 → 5,005 distinct strings).

**Predicted result of re-running stage 5a with them in place: macro_f1 ≈ 0.6366,
Trash-recall 36/180, Clear-loss 40.** That beats the shipped labels and does not raise
Clear-loss, which is `ADOPT-CANDIDATE` on the repository's own gate. The prediction comes
from the text-only witness; the full stack has to confirm it, and that is one 2.5-hour A/B.

---

## 5. Things that are already fine — checked, closing them

**The roman-numeral exemption works.** The 2026-09-10 fix (`_RE_ROMAN_TOKEN`, applied
above every clause) clears `Sonda VIII/3` and `12.VIII.1977,` as intended. The residue is
**84 lines (0.4%)**: 57 where the numeral exceeds the 7-glyph cap (`CCLXXXVII`), 27 where
OCR has mixed the case (`XXxIX/1469-1477`). Only 15 of the 84 are currently Clear/Noisy.
Not worth a change; the known cost recorded in the code comment is the right call.

**Stage 2 parity passes** — every document delta `+0`. That is the correct result for
"the offline re-scorer reproduces what the pipeline wrote", and it is worth having. It is
*not* the rotation-divergence measurement the runbook claims it is: the 95 ARÚP / 10,258
ARUB figures were offline-vs-live on the **full collections**, and 822 delivered documents
is evidence, not that measurement. That question is still open.

---

## 6. Method: three metrics that disagreed, and which were right

**`macro_f1` is not the gate, and the class supports say why.** It averages F1 over five
classes regardless of size. With Trash at 180 and Clear at 1,305, one gold-Trash line moves
it roughly seven times as much as one gold-Clear line, so it structurally rewards pushing
the boundary toward the rare class. It said the best thing on the board about 5c (+0.0397)
— the arm with the worst Clear-loss. The current `ab_constant_eval` already demotes it to a
diagnostic; the printed supports (§7) are what make the demotion legible.

**`KL` is worse than useless here.** The arm with the best KL by a factor of six — 5c at
0.00669 against a 0.04208 baseline — is the arm everyone agrees is worst. KL compares
*marginal* category distributions, so an arm can reach the right Trash total with entirely
the wrong Trash lines and score beautifully. It should never appear in an adoption
argument.

**`Clear-loss` and `costed_score` were right every time**, including where they contradicted
`macro_f1`. Keep the gate where it is.

**One correction to my own framing of 5c.** It is not statistically null. Turning on
`SHORT_GARBAGE_LEXICON_CONVICT` is +44 Trash catches for +21 Clear losses, exact McNemar
p ≈ 0.006 — a real effect, and the largest single gain anything in #30 has produced. It is
still a reject: a 50% rise in Clear-loss fails the gate outright, and the fixture evidence
agrees (5 of 31 pinned vocabulary fixtures misjudged at `MIN_DF` 3). But the question it
leaves open is a threshold and a table, not the mechanism — it is the only thing in the
module that reaches `edelite`.

**Line counts are the wrong unit, and the issue's own premise turns on it.** 20,324 lines
are 5,243 distinct strings. By line, 78.3% of witness fires are on 2010+ documents — which
is what #30 is titled about. By distinct string, **2,907 are pre-2000 against 1,341 for
2010+**. The 2010+ concentration is repetition in database exports; the *variety* of OCR
damage is in the older scans. A rule tuned on line counts is tuned on the repetition.

---

## 7. Changes made

All four are in the attached files. Nothing is pushed. Repository test suite:
**1,197 passed, 14 skipped, 2 xfailed** — identical to the unmodified baseline; `ruff check`
and `ruff format --check` clean on every file touched.

**`text_util.py`** — the two guards from §4, both witness-local and inert while
`SHORT_GARBAGE_WITNESS_ENABLE` is false.
* `has_expected_lang_diacs()` + `_expected_lang_diacritics()` — vetoes on a diacritic of
  any `EXPECTED_LANGS` language instead of Czech alone, by unioning the `_LANG_DIACRITICS`
  entries the module already carries. Kept separate from `has_cz_diacs()`, which is read at
  fifteen other sites whose meaning is specifically "Czech".
* `_RE_FUSED_GRID_REF` — the unhyphenated twin of a shape `is_domain_notation()` already
  accepts.

**`setup/config.txt`** — comments only; all 144 key/value lines byte-identical. Replaces
the falsified "DO NOT TURN IT ON WITHOUT A LEXICON" block with the gold table and the
`cuxoaid` result; closes the vowel-run question at 3 on the 5b evidence; records 5c's gold
numbers against the convict clause; corrects the de-gemination counts and notes the
one-family reach.

**`tools/ab_constant_eval.py`** — `mcnemar_exact()` and the paired comparison already
landed at HEAD; what was missing is the denominator that §1 turns on.
* `_print_class_supports()` — the gold class supports, once, above the verdicts.
* `wilson_interval()` — 95% interval printed beside each arm's Trash-recall.
* `Trash-recall` now prints as `0.1222 (22/180)` rather than a bare rate.

**`tools/short_garbage_witness_report.py`** — the distinct-string count moves into the
default exposure block instead of appearing only under `--distinct`, with the
lines-per-string ratio and the most-repeated string. Every ratio ever quoted from that
block, the "1:3 against" included, was a line ratio.

**`issue30_runbook_job.sh`** — 5a relabelled as the shipping candidate and 5a-bis as the
control; the tool-version gap recorded with the `FORCE=1` re-run instruction; the
denominator stated in the trailer. Two new stages: **5d** (`GEMINATE_RATIO` 0 vs 4 — the
only change between the 09-17 and 09-18 numbers, never measured alone) and **5e**
(`LEXICON_MIN_DF` 2 vs 3 — the config calls 2 marginally best on self-scored data and it
has never been checked against gold).

### Not changed, deliberately

No flag is flipped. No threshold moves. No production predicate is widened —
`is_domain_notation()` keeps its near-miss, because fixing it there changes live behaviour
for seven strings and belongs behind its own parity re-score.

---

## 8. Corrections to the record

* **"only ~1,370 distinct strings"** (2026-09-17 comment) → **5,243**. 1,341 is the 2010+
  slice alone. The in-tree runbook comment already carries the right figure; the issue
  thread does not.
* **`ppole` "across 22 documents"** → **25** in the witness queue; df 35 corpus-wide.
* **The "1:3 against → 1.7:1 in favour" table** is scored against `categ`. Against gold the
  ordering reverses on every column, and 90.5% of the veto's credited benefit was one
  string that belongs in Trash.
* **`Trash-recall` denominators**: 180, not 90. A reader reconstructing the paired counts
  from the logs alone can land on either.
* **`setup/config.txt`'s "36 below 2×"** → 51 (both forms attested at `MIN_DF`) or 66 (twin
  at any frequency).
* **`30.runbook.md` does not exist in the repository.** It is cited as the authority for
  "do not enable without the measurement" by `text_util.py`, `setup/config.txt` and
  `tools/build_token_lexicon.py`. Only the job script exists, on the cluster.
* The 09-17 comment noted it was recording *"the second time in this round that
  fixture-level intuition inverted on real data"*. This is the third, and the pattern is
  sharper than "intuition": **every figure scored against `categ` has inverted when gold
  arrived.** `categ`-scored exposure is good for sizing an annotation queue and has not
  once been right about a direction.

---

## 9. What to do next, in order

1. **Re-run stage 5a with the two guards** (`FORCE=05a_witness_ab`, ~2.5h). If Clear-loss
   comes back 40 at Trash-recall 36/180, `SHORT_GARBAGE_WITNESS_ENABLE` is adoptable on the
   repository's own gate — and that is the decision #30 has been waiting on since July.
   Flipping it also means moving the four `SHORT_GARBAGE_WITNESS_*` constants out of
   `_DELIBERATELY_NOT_TUNABLE` and re-adding `rule_short_garbage_witness` to the two
   ablation lists, in the same commit.
2. **Re-run the whole of stage 5 on current code** (`FORCE=1`, ~15h with 5d and 5e). The
   logs in hand predate the `errors` column, McNemar, and the current adoption gate.
3. **Annotate the distinct queue.** This is the binding constraint now, not the absence of
   gold. After the guards the queue is 5,005 distinct strings, of which **1,688 are never
   currently Trash** — those are the ones that decide the flag. Setting the `ppole` family
   aside as the single decision it is, the remaining 1,674 strings cover 2,670 lines with
   no short head: top 10 settle 19%, top 250 settle 47%. It is genuinely 1,674 decisions,
   and they are the only thing that can tell a wrong witness from a wrong pipeline.
4. **Stage 6 as its own job** (`RUN_STAGE6=1`, ~87h). Every `DEAD` / `LOAD-BEARING` /
   `clear_loss` verdict quoted in #30, the 23-rule sweep included, was scored against the
   pipeline's own output. `--split-cascade` is also the only instrument for the standing
   27% document-post-processing caveat.
5. **Do not rebuild the lexicon to fix the veto** (§3). Rebuild it if a wider table is
   wanted for other reasons, but `cuxoaid` at df 4 and `Naiade` at df 0 are not a sparsity
   problem and a bigger corpus moves them the wrong way.
