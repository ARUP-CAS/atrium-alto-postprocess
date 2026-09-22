# What we need from you on issue #30, and why

**For:** @david-spacil
**Issue:** [ufal/atrium-alto-postprocess#30](https://github.com/ufal/atrium-alto-postprocess/issues/30)
**Time needed:** items 1 and 2 are one short reply each; item 3 is a judgement call; item 4 is the
one nobody else can answer.

**Changed since the last version of this document (2026-09-21):** the run we asked you to
sanity-check in the old item 1 has happened, and it passes — that item is now closed and reported
rather than asked. The dedup decision in the old item 2 now has a corpus-wide denominator instead
of a 822-document one, which changes the recommendation from "probably" to "clearly". Two new
items are here because the full-collection pass raised them.

---

## 0. Where we are, in eight lines

Your patch is merged and measured: 367,208 lines lifted, 76.5% right / 9.6% borderline / 13.9%
wrong on 484 blind-graded lines, about 26,000 rubbish lines now reaching `Clear`.

The shape witness — the narrower rule meant to pay that down — **passes its adoption gate**, as of
stage 8. Errors 513 → 503, `Clear`-loss unchanged at 40, cost down, p = 0.013. Your Roman-numeral
finding is closed and stayed closed.

The flag is still off, and the reason has changed. It is no longer the `Clear`-loss criterion and
it is no longer waiting on annotation. We found that the run measuring *how much text the rule
would affect* was made with the vocabulary dictionary switched off — a configuration we will never
ship — and that with it on, about three quarters of the apparent risk is not risk at all. We are
re-running that measurement before deciding. Nothing about your patch or your gradings is affected.

---

## 1. The run you were asked to sanity-check has happened, and it passes

You were asked, in the previous version of this document, whether the 503 / 40 figure looked wrong
before we spent a run on it. We spent the run. The figure was real.

Stage 08b is a proper paired A/B over `SHORT_GARBAGE_WITNESS_ENABLE` itself, one output directory,
both arms in one process:

```
False: macro_f1=0.6173  errors=513  Clear-loss=40  cost=0.2917  -> parity
True : macro_f1=0.6344  errors=503  Clear-loss=40  cost=0.2829  -> ADOPT-CANDIDATE
       paired vs False: fixes 12, breaks 2 (effective n=14)  exact McNemar p=0.01294
```

`Trash`-recall goes 12.2% → 18.9% (95% CI 13.8–25.2%). The adoption gate — no increase in errors,
cost or `Clear`-loss — is satisfied on all three.

**And the 42 → 41 → 40 drift is explained.** Both arms of this single run report 40. The drift was
between trees, not within a measurement: three runs on three different working states, not three
answers to one question. Nothing needs root-causing further.

**No action needed from you on this item.** It is here because you were asked for an opinion on it
and you are owed the outcome.

## 2. The de-duplication decision — now costed on the whole corpus

You have had this question since Round 2. It has been answered on a sample twice; this is the
first time it is answered on both collections in full.

**The mechanism.** `apply_document_postprocessing()` gives every copy of an identical line in a
document the same category — whichever the majority got. So if the witness convicts three copies
of a word and two were correct, those two are pulled down with them.

**How big it is, corpus-wide** (61,682 groups over both archives, against the 5,222 the earlier
answer was based on):

|                                                              |                         |
|--------------------------------------------------------------|-------------------------|
| (document, string) groups the step votes on                  | 61,682                  |
| of those, **unanimous** already                              | 61,359                  |
| contested at all                                             | 323                     |
| decided by a strict majority                                 | 143                     |
| decided by a tie                                             | 180                     |
| **groups your option 2 would change**                        | **0**                   |
| `Clear` lines the vote pulls down                            | 24 (16 groups)          |
| `Trash` lines the vote rescues                               | **305** (244 groups)    |
| **net**                                                      | **+281 in its favour**  |

The margin is *wider* at full scale than on the sample, where it was 31 rescued against 17 lost.
And the tie case remains structurally impossible to harm you: `mode()[0]` returns tied values
sorted, and `Clear` < `Noisy` < `Trash`, so none of the 180 ties can land on `Trash`. That is an
accident of the alphabet rather than a design, and it is load-bearing — worth knowing if anyone
ever renames a category.

**The three options, with the corpus-wide numbers:**

1. **Accept.** The step is a net rescuer by roughly twelve to one.
2. **A/B the eight page-smoothing constants.** Config-driven, costs nothing, still not run.
3. **Stop a bare majority demoting `Clear` → `Trash`.** Measured reach across both collections:
   **zero groups.** The case it was written for does not occur.

**Our recommendation is 1, and we think 3 can now be retired** — not because it was a bad idea, but
because it has been measured on the population it would run against and has nothing to act on.
**The choice is still yours**; one line is enough.

## 3. Please re-score your 508 against the current predicate

Unchanged from the last version, and still open.

Your measurement was the gate, and it was right: 26 lines moved, 12 fixed, 12 broken, every break
carrying a Roman numeral. Since then the predicate has gained a Roman-numeral exemption, a Latin
family-suffix exemption, a fused grid-reference exemption, the de-gemination guard (see item 4) and
now a URL/e-mail exemption (item 5).

On the full 2,064-line gold set the rule now fixes 12 and breaks 2. Your 508 are a subset, so
breaks within your sample are bounded by set inclusion — sound but indirect. It was your finding
and your tooling; a direct figure on the 508 closes it properly.

## 4. The eight doubled-initial tokens — and the last automatic test for them has failed

This is the item only you can answer, and it is now the *only* remaining approach.

On 2026-09-19 you told us `ppole` is an abbreviation for *popelnicová pole*, and that the other
doubled-first-letter examples really are scanning errors. We have since tried three ways to make
that distinction automatic:

1. **Ratio to the base word** — `ppole` sits fifth of seven. Fails.
2. **Absolute document frequency** — separated cleanly on 822 documents (35 against ≤ 8); on all
   113,100 it is 229 against 195. Fails.
3. **Per-collection concentration** — the idea you would expect to work: a scanner artefact belongs
   to the run that produced it, an abbreviation is a shared convention. Stage 08a measured it:

| token       |  ARUP |    ARUB |                  |
|-------------|------:|--------:|------------------|
| **`ppole`** | **3** | **226** | the abbreviation |
| `ssuti`     |   152 |      43 | artefact         |
| `ssutí`     |   116 |      26 | artefact         |
| `ssutě`     |    46 |      18 | artefact         |
| `llocm`     |    44 |      11 | artefact         |
| `vvkop`     |     1 |      29 | artefact         |
| `jjámy`     |     2 |       8 | artefact         |
| `oobjekt`   |     2 |       2 | artefact         |

**The abbreviation is the most collection-concentrated token of the eight.** The test does not
merely fail to separate them, it inverts — `ppole` looks more like an artefact than any artefact
does, because it is a convention of ARUB's own 2010s forms rather than of the archive as a whole.
(Separately measured: `ppole` is 2 lines in the 1990s, 45 in the 2000s, 13,144 in the 2010s. It
arrives with the forms.)

**So there is no frequency-shaped signal left.** Two questions follow, and one line each is plenty:

* **At this scale, are `ssuti` (195 documents), `ssutí` (142) and `ssutě` (64) still scanning
  errors?** Appearing in 195 separate documents is not what we would expect from a scan artefact,
  and it is close to `ppole`'s 229. Either the misread repeats across a very large number of scans
  of the same form — which is plausible — or some of them are conventions too, and the
  822-document reading was too small to show it.
* **Given no automatic test works, should the de-gemination guard be removed?** Setting
  `SHORT_GARBAGE_LEXICON_GEMINATE_MAX_DF = 0` falls back to plain attestation. Keeping it means
  keeping a constant we know is fitted to one table and is wrong on 5 of 7 tokens at full scale.
  We have not changed it, because at this point that is a judgement and not a measurement.

## 5. Two predicate findings, one of which we got wrong first

Reported because we have made a point of telling you when our own summaries did not survive
contact with the data, and this is a case where we caught ourselves.

**What we thought we had found.** `Lepus europaeus`, `Mammalia indet.` and `Triticum monococcum`
all trip the witness on the shipped predicate, while `Poaceae` does not — apparently a gap where
the Latin-family exemption fails to cover binomial species names, which would matter a lot in the
osteology and archaeobotany reports.

**What is actually true.** We had tested with the vocabulary dictionary switched off — the same
mistake that produced the sizing error in § 0. Every one of those terms is attested in the
full-collection dictionary and is already exempt once it is loaded. There is no gap, and we did
not add a rule for one. We drafted a "genus + species" pattern before checking, measured it, and
found it would also have exempted `Chenopoaium hycnaum`, `Loua (oxkuku` and `Laaid. bazic 64999/`
— buying false negatives to fix a problem that did not exist.

**What was a real gap.** Web addresses and e-mail addresses **quoted once**. The footer URLs are
attested by sheer repetition, but a citation appearing in a single document can never be attested
by a document-frequency table, by construction. 144 such lines survive a configured dictionary:

```
(zdroj: http://www.turistika.cz/mista/krakovec-mistni-cast-laskova).
1 https://www.mza.cz/indikacniskici/skica/detail/1669
roku 1820 (http://www.hrady.cz/index.php?OID=1291).
e-mail: officeauappmost.cz          <- the scan lost the @; the label survived
```

`is_domain_notation()` now recognises the shape — 0 misses on those 144, 0 false positives against
the other 7,289 at-risk lines and against the pinned garbage fixtures. **No action needed**, it is
mentioned so that the item-3 re-score is run against a predicate you know the current shape of.

**And one class we have deliberately left broken.** `Kaukasus`, `Hallstatthaus` and
`Schuhleistenkeilbruchstueck` are real words, too rare across documents to be attested, convicted
for having too few distinct letters. There is no length or letter-ratio cut that separates them
from real rubbish of the same shape — `vodovod` and `PSSPPOP` are both seven letters at the same
ratio; `VODOVOD` and `PSSPPOP` are both all-caps. Tuning a threshold on two examples is exactly
what we did with the de-gemination cap in item 4, and item 4 is what that costs. It is recorded as
known debt with a test pinning it.

## 6. A definitional question we would like you and @DanaKriv to settle

The full-collection pass turned up something that is not a bug and may be more consequential than
the flag.

**77% of what the program discards in this part of the archive has nothing wrong with it** — no
garbled characters, no odd glyphs. Concretely, it currently stores as `Trash`: `http://www.arub.cz`
(5,309 lines, scanned correctly), `e-mail: mhauer@zip-ops.cz`, and `ARCHAIA Brno o.p.s.` — while
storing `ARCHAIA` on its own as `Clear`.

Against the definitions in use — `Clear` is correct text, `Noisy` is damaged but readable, `Trash`
is *nobody can read this* — none of those is `Trash`. One label is being asked two questions:
**can a person read this** (legibility) and **is this prose worth indexing** (usefulness). The
scheme already has `Non-text` for the second and it is not being used that way.

This needs deciding **before** the annotation, not after: an annotator applying the definitions as
written will mark a correctly-scanned URL `Clear`, the rule's measured accuracy will move, and
nobody will be able to attribute the change. Either answer works — fix the program to match the
definitions, or rewrite the definitions and route footers and form labels to `Non-text`. The same
question is § 7.2 of @DanaKriv's guide.

## 7. Two small items

**7.1 Is the raw-perplexity thread finished?** The 367,208 lines arrived via filesender and we read
them through `tools/issue30_perplex_report.py`. If nothing further was intended, we will close it.

**7.2 Corrections to things we told you previously.**

* We reported 07b as *"`QUALITY_VOCABULARY_ENABLE` has zero effect on the gold set"* and then as
  *"void, not zero"*. It is now measured: **a decisive reject.** 212 fixes against 540 breaks,
  `Clear`-loss 40 → 180. It buys `Trash`-recall of 78% by destroying 14% of all good lines, and
  what it destroys is the archive's own register — site codes, inventory numbers, citations, place
  names with administrative qualifiers. Not a language problem: only 3% of the destroyed lines are
  German, 55% are Czech.
* We reported 07c's symbol-strip result as void. It is now measured as a genuine **null**: 5 fixes,
  5 breaks, p = 1.
* We reported the de-duplication blast radius as 7 groups / 22 lines. That was correct for the
  sample it was measured on; item 2 above is the corpus-wide figure and supersedes it.

---

Thank you — item 4 is the one nobody else can answer, and item 6 is the one that would save the
most rework if it is settled before the labels come back.
