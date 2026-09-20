# What we need from you on issue #30, and why

**For:** @david-spacil
**Issue:** [ufal/atrium-alto-postprocess#30](https://github.com/ufal/atrium-alto-postprocess/issues/30)
**Time needed:** one short reply for items 1 and 4; item 2 is a judgement call; item 3 is a re-run on your side.

---

## 0. Where we are, in six lines

Your patch is merged and measured: 367,208 lines lifted, 76.5% right / 9.6% borderline / 13.9%
wrong on 484 blind-graded lines, about 26,000 rubbish lines now reaching `Clear`.

The shape witness — the narrower rule meant to pay that down — is in the tree, switched **off**.
Your Roman-numeral finding (12 fixed, 12 broken) is closed: with the exemptions added, the same
rule now fixes 14 and breaks 1 on the full 2,064-line gold set.

The flag has stayed off because the adoption rule rejects any change that loses even one `Clear`
line. **That may no longer be the situation** — see item 1.

We re-read the whole stage-7 delivery against its own log files last week and found three of our
own conclusions were wrong. Two of those bear directly on questions we put to you, so they are
corrected here rather than left for you to find.

---

## 1. Please sanity-check a result before we act on it

This is the most important item and it should take five minutes.

Stage 07d was run to settle a different question (the vowel-run threshold). Both of its arms
have the witness switched **on**, and both print this:

```
3.0: macro_f1=0.6344  errors=503  Clear-loss=40  cost=0.2829  -> ADOPT-CANDIDATE
4.0: macro_f1=0.6324  errors=503  Clear-loss=40  cost=0.2829  -> ADOPT-CANDIDATE
```

Against the shipped configuration (513 errors, `Clear`-loss 40, cost 0.2917) that is **ten fewer
errors, lower cost, and no `Clear` lines lost**. The adoption rule is satisfied. Every other
document we have written still says the flag is rejected on `Clear`-loss +1.

Two reasons we are not simply switching it on:

* **07d's base configuration is not printed in the log.** We infer it is witness-on with the
  vocabulary table configured, because the `Trash` recall (34/180) matches the runs that had the
  table and not the one that did not. That is an inference from a number, not a line in a log.
* **The same nominal configuration has now reported `Clear`-loss 42, then 41, then 40**, across
  round 1, round 2 and 07d. We have never explained the drift. It is two lines, and two lines is
  the entire margin the decision turns on.

**What we are going to do:** one A/B over `SHORT_GARBAGE_WITNESS_ENABLE` itself, on the stage-7
tree, from a single output directory, with a `--no-postprocessing` companion. That settles both
questions in one run.

**What we would like from you:** does anything about the 503 / 40 figure look wrong to you before
we spend the run? You have measured this rule independently once already and caught something we
missed. If the number is real, the flag decision is probably makeable without waiting for any
more annotation.

---

## 2. The de-duplication decision — now costed on both sides

You have had this question since Round 2, and until now only one side of it had numbers. Both
sides do now.

**The mechanism.** `apply_document_postprocessing()` gives every copy of an identical line in a
document the same category — whichever the majority got. So if the witness convicts three copies
of a word and two were correct, those two are pulled down with them.

**How big it actually is.** Measured on the 20,078-line candidate queue:

|                                                                   |                  |
|-------------------------------------------------------------------|------------------|
| (document, string) groups the step votes on                       | 5,222            |
| of those, **unanimous** already                                   | 5,200            |
| contested at all                                                  | 22 (755 lines)   |
| **decided by a bare majority or a tie** — what option 2 would fix | **7 (22 lines)** |

4,903 of the 5,222 groups are a single line. And the witness is a pure function of the line's
text, so inside a group it convicts **all or none** — it cannot create a split, only move a group
that is already unanimous.

**And the step is currently helping, not hurting.** Comparing stage 5a (cleaning on) with 5f
(cleaning off) on the same gold set:

|                  | fixes | breaks | baseline `Clear`-loss |
|------------------|------:|-------:|----------------------:|
| cleaning **on**  |    14 |  **1** |                    40 |
| cleaning **off** |    14 |  **3** |                    55 |

The cleaning step removes two of the witness's three mistakes, and 15 more from the baseline. The
two lines that originally motivated changing it — `CTX194503132` and `MTX197902086` — are among
the ones it already smooths over.

**The three options, ranked by what the data says:**

1. **Accept.** With the cleaning step in place the observed cost is **+1 `Clear`-loss for −13
   errors**, p = 0.001. (Per-line, with the step removed, it is +2 for −11 at p = 0.013.)
2. **A/B the eight page-smoothing constants.** All config-driven, costs nothing, still not run.
3. **Stop a bare majority demoting `Clear` → `Trash`.** A production-wide change whose measured
   reach in this population is **22 lines**, and which gives up a step that is currently net
   positive here.

We think the order is 1, then 2, then 3. **The choice is yours** — changing a smoothing step that
touches about 27% of this population on a reading rather than a measurement is how this issue has
gone wrong three times already, so nothing moves until you pick one.

---

## 3. Please re-score your 508 against the current predicate

Your measurement was the gate, and it was right: 26 lines moved, 12 fixed, 12 broken, every break
carrying a Roman numeral.

Since then the predicate has gained four narrowings:

* a Roman-numeral exemption, above all four clauses (`I` is a vowel, so exempting the
  triple-letter clause alone would have fixed nothing — `VIII` still fired the vowel-run clause);
* a Latin taxonomy exemption (`-aceae` and relatives), after we found the vowel-run clause
  convicted **10 of 10** botanical family names;
* an exemption for fused grid references such as `S-VIIIb`;
* the de-gemination guard (see item 4, which has since become a problem).

On the full 2,064-line gold set the rule now fixes 14 and breaks 1. Your 508 are a subset of
that set, so breaks within your sample are bounded at 1 **by set inclusion** — which is sound but
indirect. It was your finding and your tooling, and a direct figure on the 508 alone closes it
properly.

---

## 4. A correction, and a question only you can answer

On 2026-09-19 you told us `ppole` is an abbreviation for *popelnicová pole*, not a scanning
error, and that the other doubled-first-letter examples in `issue30_gold_ab_findings.md` really
are scanning errors. That was right and it reversed one of our conclusions.

We then built a guard on it. The idea was: a scanning error appears in a handful of documents, an
abbreviation appears in many, so put a ceiling on how many documents a doubled token may appear
in. On the 822-document table this separated cleanly — `ppole` at 35 documents, every confirmed
artefact at 8 or below.

**We then rebuilt the dictionary over all 113,100 documents, and the separation disappeared:**

| token       | documents | base word |    ratio |
|-------------|----------:|----------:|---------:|
| **`ppole`** |   **229** |     8,600 |    37.6× |
| `ssuti`     |       195 |     1,667 |     8.5× |
| `ssutí`     |       142 |     1,617 |    11.4× |
| `ssutě`     |        64 |       900 |    14.1× |
| `llocm`     |        55 |       417 |     7.6× |
| `vvkop`     |        30 |     1,400 |    46.7× |
| `jjámy`     |        10 |    14,799 | 1,479.9× |

Neither column separates the abbreviation from the artefacts any more. By ratio `ppole` sits
fifth of seven. By document count it is 229 against 195 — a 17% margin where there used to be a
4.4× gap. We have left the constant alone, added a warning, and written up why fitting a
threshold to this table would be a mistake.

**Our question:** at this scale, are `ssuti` (195 documents), `ssutí` (142) and `ssutě` (64)
still scanning errors? Appearing in 195 separate documents is not what we would expect from a
scan artefact, and it is close to `ppole`'s 229. Two possibilities we cannot choose between:

* they really are scanning errors, and the misread simply repeats across a very large number of
  scans of the same kind of form; or
* some of them are conventions or abbreviations too, and the 822-document reading was too small
  a sample to show it.

One line per token is enough. This decides whether there is a signal worth building on at all,
or whether the de-gemination guard should simply be removed.

---

## 5. Two small items

**5.1 Is the raw-perplexity thread finished?** The 367,208 lines arrived via filesender and we
read them through `tools/issue30_perplex_report.py`. If nothing further was intended, we will
close that thread.

**5.2 Two of our own results were wrong, and we are telling you because you may have read them.**

* We reported stage 07b as *"`QUALITY_VOCABULARY_ENABLE` has zero effect on the gold set"*. It
  is **void, not zero** — the comparison never switched the flag on. The function that loads the
  vocabulary caches its answer on first use, both arms of the comparison run in one process, and
  the second arm read the first arm's cached result. This is the same defect as 07c, which we had
  already found and fixed once; the fix covered one form of it and not the general case. Both are
  fixed now and both runs are being repeated.
* We reported stage 07a as confirming the de-gemination guard at full scale. It refutes it — see
  item 4 above.

Neither changes anything you have measured. We are flagging them because our summary of a run has
now been wrong three times where the run's own log was right, and the standing fix is to read the
log.

---

Thank you — item 1 is the one that unblocks things fastest, and item 4 is the one nobody else can
answer.
