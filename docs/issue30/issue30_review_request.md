# What we need from you on issue #30, and why

**For:** @david-spacil
**Issue:** [ufal/atrium-alto-postprocess#30](https://github.com/ufal/atrium-alto-postprocess/issues/30)
**Time needed:** items 1 and 2 need one short reply each. Item 3 is a judgement call. Item 4 is the
one nobody else can answer.

**What changed since the last version (2026-09-22).** Stage 6, an 87-hour measurement, has
finished. It answers your standing objection that our figures were graded by the program against
its own output. It also produced one number that affects item 2. See § 7.2.

*Earlier, on 2026-09-21:* the run we asked you to sanity-check has happened and it passed, so that
item is now reported rather than asked. The de-duplication question in item 2 now has a figure
measured across both whole collections, instead of one measured on 822 documents. That changes our
recommendation from "probably" to "clearly".

**A note on wording.** This document used to use our internal shorthand. We have rewritten it in
plain English. Where a technical term is genuinely needed, it is explained the first time it
appears.

---

## 0. Where we are, in eight lines

Your patch is merged and measured. It moved 367,208 lines back toward being kept. A human graded
484 of them: 76.5% right, 9.6% borderline, 13.9% wrong. The price is about 26,000 rubbish lines
that are now kept as good text.

The **shape witness** — the narrower rule meant to clean those up — **passes its acceptance test**
as of stage 8. Errors fell from 513 to 503, readable lines lost stayed at 40, and the cost measure
went down. Your Roman-numeral finding is closed and has stayed closed.

The rule is still switched off, and the reason has changed. It is no longer the readable-lines
criterion, and it is no longer waiting for annotation. We discovered that the run which measured
*how much text the rule would affect* was made with the vocabulary dictionary switched off — a
setting we would never ship. With the dictionary on, about three quarters of the apparent risk is
not risk at all. We are re-running that measurement before deciding. **Nothing about your patch or
your gradings is affected.**

---

## 1. The run you were asked to check has happened, and it passed

In the previous version we asked whether the "503 errors / 40 lines lost" figure looked wrong to
you before we spent a run on it. We spent the run. The figure was real.

Stage 8b compares the rule switched off against the rule switched on, in one process, writing to
one place — so the two halves cannot differ for any reason except the rule itself:

```
OFF: errors=513  readable lines lost=40  cost=0.2917
ON : errors=503  readable lines lost=40  cost=0.2829
     line by line: 12 lines fixed, 2 lines broken, significance p=0.013
```

The rule also finds more of the rubbish it is meant to find: 12.2% → 18.9% of the lines a human
called `Trash` (the range of uncertainty on that is 13.8%–25.2%). Our acceptance test asks for no
increase in errors, no increase in cost, and no increase in readable lines lost. All three hold.

**And the drift is explained.** The same setting had reported 42, then 41, then 40 readable lines
lost, and we could never account for it. Both halves of this single run report 40. The differences
were between three different working versions of the code, not three different answers to one
question. There is nothing left to investigate.

**No action needed from you here.** It is included because you were asked for an opinion and you
are owed the outcome.

## 2. The de-duplication decision — now measured on the whole archive

You have had this question since Round 2. It has been answered twice on samples. This is the first
answer measured on both collections in full.

**The mechanism.** When the same line of text appears several times in one document, a cleaning
step gives every copy the same category — whichever category the majority of the copies received.
So if the new rule condemns three copies of a word and two of those copies were correct, the two
correct ones are pulled down as well.

**How big it is across the whole archive.** The earlier answer was based on 5,222 groups. This one
covers 61,682:

|                                            |                                     |
|--------------------------------------------|-------------------------------------|
| groups of repeated lines the step votes on | 61,682                              |
| of those, already unanimous                | 61,359                              |
| contested at all                           | 323                                 |
| decided by a clear majority                | 143                                 |
| decided by a tie                           | 180                                 |
| **groups your option 3 would change**      | **0**                               |
| readable lines the vote pulls down         | 24 (in 16 groups)                   |
| rubbish lines the vote rescues             | **305** (in 244 groups)             |
| **net effect**                             | **+281 lines in the step's favour** |

The margin is *wider* at full scale than it was on the sample, where it was 31 rescued against 17
lost.

Ties also cannot hurt you, for a reason worth knowing. When the vote is tied, the code picks the
first category in alphabetical order, and `Clear` comes before `Noisy`, which comes before `Trash`.
So a tie can never land on `Trash`. That is an accident of the alphabet rather than a design
decision, and it is holding weight — worth remembering if anyone ever renames a category.

**Your three options, with the full-archive numbers:**

1. **Accept it as it is.** The step rescues about twelve lines for every one it costs.
2. **Test the eight page-smoothing settings.** They are all controlled by configuration, so this
   costs nothing to try. Still not done.
3. **Stop a bare majority from pushing a readable line into `Trash`.** Measured reach across both
   collections: **zero groups.** The situation it was written for does not occur.

**We recommend option 1, and we think option 3 can now be dropped** — not because it was a bad
idea, but because it has been measured against the data it would run on and has nothing to act on.
**The decision is still yours.** One line is enough.

## 3. Please re-check your 508 lines against the current rule

Unchanged from the last version, and still open.

Your measurement was the deciding one, and it was right: 26 lines moved, 12 improved, 12 made
worse, and every one of the 12 failures contained a Roman numeral.

Since then the rule has gained four exceptions: Roman numerals, Latin family names, joined grid
references such as `S-VIIIb`, and the doubled-letter guard described in item 4. It has now also
gained a web-address exception, described in item 5.

On the full set of 2,064 annotated lines the rule now improves 12 and worsens 2. Your 508 lines are
part of that set, so the number it worsens within your sample cannot be more than 2 — which is
sound reasoning, but indirect. It was your finding and your tooling, and a direct figure on the 508
would close it properly.

## 4. The eight doubled-letter tokens — every automatic test has now failed

This is the item only you can answer, and it is now the **only** approach left.

On 2026-09-19 you told us that `ppole` is an abbreviation for *popelnicová pole*, and that the
other doubled-first-letter examples really are scanning errors. Since then we have tried three ways
to make that distinction automatically:

1. **Compare it to the base word.** `ppole` sits fifth of seven. No use.
2. **Count how many documents it appears in.** On 822 documents this separated cleanly: `ppole` in
   35 documents, every confirmed error in 8 or fewer. Across all 113,100 documents it becomes 229
   against 195. No use.
3. **Check whether it is concentrated in one collection.** This is the one you would expect to
   work: a scanning error belongs to the machine that produced it, while an abbreviation is a
   shared convention. Measured:

| spelling    |  ARÚP |    ARUB |                  |
|-------------|------:|--------:|------------------|
| **`ppole`** | **3** | **226** | the abbreviation |
| `ssuti`     |   152 |      43 | scanning error   |
| `ssutí`     |   116 |      26 | scanning error   |
| `ssutě`     |    46 |      18 | scanning error   |
| `llocm`     |    44 |      11 | scanning error   |
| `vvkop`     |     1 |      29 | scanning error   |
| `jjámy`     |     2 |       8 | scanning error   |
| `oobjekt`   |     2 |       2 | scanning error   |

**The abbreviation is the most one-sided of the eight spellings.** The test does not
simply fail — it points the wrong way. `ppole` looks more like a scanning error than any real
scanning error does, because it is a convention of ARUB's own forms from the 2010s rather than of
the archive as a whole. (Measured separately: `ppole` appears on 2 lines in the 1990s, 45 in the
2000s and 13,144 in the 2010s. It arrives with the forms.)

**So no frequency-based signal is left.** Two questions follow, and one line each is plenty:

* **At this scale, are `ssuti` (195 documents), `ssutí` (142) and `ssutě` (64) still scanning
  errors?** Appearing in 195 separate documents is not what we would expect from a scanning
  artefact, and it is close to `ppole`'s 229. Either the same misreading repeats across a very
  large number of scans of the same form — which is quite possible — or some of them are
  conventions too, and the 822-document view was too small to show it.
* **Since no automatic test works, should we simply remove the doubled-letter guard?** Removing it
  would fall back to the plain dictionary check. Keeping it means keeping a threshold that we know
  was fitted to one small table, and that is wrong on 5 of the 7 tokens at full scale. We have not
  changed it, because at this point it is a judgement rather than a measurement.

## 5. Two findings about the rule itself, one of which we got wrong first

Included because we have made a point of telling you when our own conclusions did not survive
contact with the data. This one we caught ourselves.

**What we thought we had found.** `Lepus europaeus`, `Mammalia indet.` and `Triticum monococcum`
all trigger the rule, while `Poaceae` does not. That looked like a gap: the exception for Latin
family names does not cover two-part species names, which would matter a great deal in the
osteology and archaeobotany reports.

**What is actually true.** We had tested with the vocabulary dictionary switched off — the same
mistake that caused the sizing error in § 0. Every one of those terms is in the full dictionary and
is already exempt once the dictionary is loaded. There is no gap, and we did not add a rule for
one. We had drafted a "genus + species" pattern before checking. When we measured it, we found it
would also have exempted `Chenopoaium hycnaum`, `Loua (oxkuku` and `Laaid. bazic 64999/` — letting
real rubbish through to fix a problem that did not exist.

**What was a real gap.** Web and e-mail addresses **quoted only once**. The addresses in page
footers appear so often that the dictionary recognises them. But an address cited in a single
document can never be recognised that way, by definition. 144 such lines survived even with the
dictionary loaded:

```
(zdroj: http://www.turistika.cz/mista/krakovec-mistni-cast-laskova).
1 https://www.mza.cz/indikacniskici/skica/detail/1669
roku 1820 (http://www.hrady.cz/index.php?OID=1291).
e-mail: officeauappmost.cz          <- the scan lost the @; the label survived
```

The program now recognises this shape. It catches all 144, and wrongly catches none of the other
7,289 lines at risk, nor any of our stored rubbish examples. **No action needed.** It is mentioned
so that when you re-check the 508 lines in item 3, you know the current shape of the rule.

**And one problem we have deliberately left unsolved.** `Kaukasus`, `Hallstatthaus` and
`Schuhleistenkeilbruchstueck` are real words. They appear in too few documents to be recognised by
the dictionary, and the rule condemns them for having too few different letters. There is no cut-off
on length or letter variety that separates them from real rubbish of the same shape: `vodovod` and
`PSSPPOP` are both seven letters with the same letter variety, and `VODOVOD` and `PSSPPOP` are both
capitals. Tuning a threshold on two examples is exactly what we did with the doubled-letter guard in
item 4, and item 4 shows what that costs. So it is recorded as a known, accepted problem, with a
test that will notice if it changes.

## 6. A question about definitions, for you and @DanaKriv together

The full-archive measurement turned up something that is not a bug, and may matter more than the
switch itself.

**77% of what the program throws away in this part of the archive has nothing wrong with it** — no
garbled characters, no strange symbols. Specifically, it currently marks as `Trash`:

* `http://www.arub.cz` — 5,309 lines, scanned perfectly correctly;
* `e-mail: mhauer@zip-ops.cz`;
* `ARCHAIA Brno o.p.s.` — while marking `ARCHAIA` on its own as `Clear`.

Measured against the definitions we work to — `Clear` is correct text, `Noisy` is damaged but still
readable, `Trash` is *nobody can read this* — none of those is `Trash`. Anyone can read them.

One label is being asked two different questions:

1. **Can a person read this?** That is what the definitions describe.
2. **Is this running text worth keeping and searching?** That is a different question, and it is
   the one the program seems to be answering in practice.

We first thought there was an easy answer: send page footers and form labels to **`Non-text`**.
Checking the documents properly, that does not work either — and the reason is a second problem we
should have told you about earlier.

**The five categories are defined in two places, and the definitions do not agree.** Dana's guide
defines them by *legibility*. The main `README.md` defines them by *what the program did and what
should happen next*. Three specific conflicts:

|               | Dana's guide says                                                       | `README.md` says                                                                                                                                              |
|---------------|-------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Trash`       | "scanning rubbish — nothing is lost by deleting it"                     | "should be re-processed by another OCR tool"                                                                                                                  |
| `Non-text`    | "not language at all — a table border, a page decoration, a ruler mark" | whatever the pre-filter caught: too short, too few different characters, under 30% letters — and it is meant to be searched for **site and find identifiers** |
| a legible URL | `Clear`                                                                 | can be `Trash` via an override                                                                                                                                |

The `Trash` row matters to you directly as a data provider: **"delete it" and "re-scan it with a
different OCR tool" are not the same instruction**, and which one is meant changes what you would
do with the output.

The `Non-text` row is why our easy answer fails. The program already uses `Non-text` to hold real,
meaningful content — an inventory number such as `A123/2024` is marked `Non-text` today, and the
README says that category "may be checked for identifiers of finds/sites". So it is not an empty
shelf we can move web addresses onto. Putting them there would mix two different things in one
category.

**This needs deciding before the labelling, not after.** If Dana applies the definitions as
written in her guide, she will mark a correctly scanned web address as `Clear`, the measured
accuracy of the rule will shift, and nobody will be able to tell whether that came from the labels
or from the definition.

**What we would like from the two of you** is a decision on the first question — is the label about
*legibility* or about *usefulness as text*? — and we will then make the program, the guide and the
README agree with each other, rather than continuing with three descriptions of five categories.
The same question is § 7.2 of Dana's guide.

## 7. Three smaller items

**7.1 Is the raw perplexity thread finished?** The 367,208 lines arrived via filesender and we read
them. If nothing further was intended, we will close that thread.

**7.2 Two things stage 6 settled, one of which you raised.**

Stage 6 — an 87-hour measurement of all 23 rules — finished on 2026-09-22.

* **Your objection about self-graded figures is answered.** You were right. Every verdict this
  issue quoted about which rules matter had been graded by the program against its own output,
  which cannot disagree with itself. All 23 rules are now graded against your 2,064 annotated
  lines. A detail worth having: this run puts the baseline at **40 readable lines lost**, the same
  number stage 8b reports from a completely separate job using a different tool. That is the first
  time two runs in this issue have independently agreed on anything.
* **And it produced a number that affects item 2.** Measured rule by rule against your labels,
  **the short-garbage rule destroys 7 of those 40 readable lines.** The rule your patch narrowed is
  itself part of the cost the new rule is being judged against. The short-line rule protects 31 and
  the reference-floor rule protects 10. We are not proposing to act on any of this. It changes how
  the number 40 should be read, and 40 is the number this decision has turned on since July.

One caution if you open the raw table: seven rules score *better* when removed. Five of them move
the result by less than a single annotated line out of 2,064, the run has no significance test
attached at all, and the two that clear that threshold both cost readable lines. It is not a list
of rules to delete, and we have written that into our records so that nobody reads it that way
later.

**7.3 Corrections to things we told you before.**

* We reported that the vocabulary check had "zero effect", then that the result was void. It is now
  properly measured, and it is a **clear rejection**: 212 lines improved against 540 made worse, and
  readable lines lost rising from 40 to 180. It finds 78% of the rubbish, but destroys 14% of all
  good lines to do it — and what it destroys is the archive's own style of writing: site codes,
  inventory numbers, citations, place names with administrative qualifiers. It is not a language
  problem: only 3% of the destroyed lines are German and 55% are Czech.
* We reported the symbol-stripping result as void. It is now measured and has **genuinely no
  effect**: 5 lines improved, 5 made worse.
* We reported the reach of the de-duplication step as 7 groups / 22 lines. That was correct for the
  sample it was measured on. Item 2 above is the full-archive figure and replaces it.

---

Thank you. Item 4 is the one nobody else can answer, and item 6 is the one that would save the most
rework if it is settled before the labels come back.
