# What the archive actually looks like to the text-quality program

**For:** @david-spacil and @DanaKriv
**Issue:** [ufal/atrium-alto-postprocess#30](https://github.com/ufal/atrium-alto-postprocess/issues/30)
**Why this exists:** every other document in this issue is about a decision. This one is about
the corpus, because the stage-8 run was the first to look at **all 113,100 documents** rather than
a 822-document sample, and what it found says more about the archive than about the algorithm.

Nothing here asks you for anything. The two documents that do are
[`issue30_annotation_guide.md`](issue30_annotation_guide.md) (@DanaKriv) and
[`issue30_review_request.md`](issue30_review_request.md) (@david-spacil).

---

## 0. The one-paragraph version

The program sorts every scanned line into `Clear`, `Noisy`, `Trash`, `Non-text` or `Empty`. We
have been trying to switch on a rule that would recover rubbish currently sitting in `Clear`. To
size the risk we measured every short line in both collections — 56.6 million lines read, 7.5
million in scope, 100,824 that the rule can reach. **The four largest things it reaches are not
scanning errors.** They are an abbreviation, the excavating organisation's own name, Latin species
names, and the web addresses in your own page footers. That is not a bug in the rule so much as a
fact about the archive: **its characteristic text is not prose**, and most automatic quality tests
are built for prose.

---

## 1. The archive is two collections, and they do not write the same way

Document identifiers carry their collection and their year, so the corpus can be split without
anyone labelling anything.

|                             | ARUP (`CTX…`) | ARUB (`MTX…`) |
|-----------------------------|--------------:|--------------:|
| documents                   |        65,424 |        47,677 |
| `Mammalia` (zooarchaeology) |   1,142 lines |           159 |
| `Lepus europaeus`           |           902 |            92 |
| `ppole`                     |        **11** |    **15,662** |
| `http://www.arub.cz`        |             0 |         5,309 |

The osteological vocabulary lives in ARUP; `ppole` and the footer URLs are ARUB. This matters
beyond bookkeeping, because it broke the last idea we had for telling abbreviations from scanning
errors automatically — see §4.

## 2. The modern half of the archive is a different kind of document

This issue is titled *"Algorithm change for 2010+ years documents"*, and the full-collection pass
is the first measurement that shows why that framing was right.

|   decade | lines the rule reaches | of those, currently kept as good text |      rate |
|---------:|-----------------------:|--------------------------------------:|----------:|
|     1950 |                  6,444 |                                 2,493 |     38.7% |
|     1970 |                  4,902 |                                 1,177 |     24.0% |
|     1990 |                  5,353 |                                 1,121 |     20.9% |
|     2000 |                 14,593 |                                 5,508 |     37.7% |
| **2010** |             **40,926** |                            **20,083** | **49.1%** |
|     2020 |                 16,489 |                                 3,817 |     23.1% |

**Two thirds of the entire risk sits in documents from 2010 onwards.** And the *reason* lines get
flagged changes completely across that boundary:

|                                | pre-2010 | 2010 onwards |
|--------------------------------|----------|--------------|
| vowel run (`oueussd`)          | 76%      | 23%          |
| doubled first letter (`ppole`) | 8%       | **66%**      |
| too few distinct letters       | 14%      | 9%           |

Older documents are typed or printed prose that the scanner damaged. **Newer documents are forms**
— structured excavation records with short field values, one or two words per line: `KULTURA:
ppole`, `Čtverec: 13/14 Sonda: - Jiné: -`, `sonda/kontext: JZ`. A rule written to catch damaged
*words* meets, in the modern half of the archive, a population of *field values*, and 96% of what
it flags there is a single legitimate abbreviation.

`ppole` itself has a birth date, which is the clearest evidence that it is a convention rather
than damage:

| decade | 1990 | 2000 |       2010 |  2020 |
|--------|-----:|-----:|-----------:|------:|
| lines  |    2 |   45 | **13,144** | 2,482 |

## 3. What the rule actually reaches, once you look at all of it

Of the 36,744 lines that are currently kept as good text and would be newly discarded:

| what it is                           |  lines | distinct strings |     share |
|--------------------------------------|-------:|-----------------:|----------:|
| `ppole` and its spellings            | 15,707 |               23 | **42.7%** |
| everything else                      | 14,974 |            9,209 |     40.8% |
| `ARCHAIA` — the excavator's own name |  3,915 |              196 |     10.7% |
| Latin species names                  |  1,737 |               82 |      4.7% |
| web addresses and e-mail             |    411 |              207 |      1.1% |

**Roughly 59% is text that was read correctly.** An abbreviation for *popelnicová pole*, a company
name in a page header, `Lepus europaeus`, `Triticum monococcum`, `http://www.arub.cz`. The
question for that 59% is never "did the scanner get this right" — it plainly did — but "is this
the kind of text this project wants to keep", which is a different question and a human one.

**The good news, and it is genuinely good:** the program already has a mechanism for this. It
builds a dictionary from the archive's own words, and anything appearing across enough documents
is left alone. Measured on the stage-8 data, switching that dictionary on removes **about three
quarters of the apparent risk** — every item in the table above except the long tail. We had not
run the measurement in that configuration, which is why the annotation request currently attached
to the issue is larger than it needs to be. That is being re-cut before it reaches @DanaKriv.

## 4. The abbreviation problem has no automatic solution, and we now know that for certain

`ppole` is an OCR-plausible shape (a doubled first letter) that is actually an abbreviation. We
tried three ways to separate that class from genuine doubled-letter scanning errors like `ssuti`:

1. **How much commoner is the base word?** — `ppole` sits mid-pack among the artefacts. No.
2. **How many documents does it appear in?** — on 822 documents this separated cleanly (35 against
   8 or fewer). On all 113,100 it collapses to 229 against 195. No.
3. **Is it concentrated in one collection?** — the idea being that a scanner artefact belongs to
   the machine that made it, while an abbreviation is a shared convention. Measured:

| token       |  ARUP |    ARUB |                  |
|-------------|------:|--------:|------------------|
| **`ppole`** | **3** | **226** | the abbreviation |
| `ssuti`     |   152 |      43 | artefact         |
| `vvkop`     |     1 |      29 | artefact         |
| `jjámy`     |     2 |       8 | artefact         |

The abbreviation is **the most collection-concentrated token of the eight** — it looks more like a
scanner artefact than any actual artefact does, because it is a convention of *one institution's*
forms. The test does not fail, it inverts.

**So there is no frequency-shaped signal that separates a local convention from a local scanning
error.** This is the concrete reason @david-spacil's reading of those eight tokens is not a
formality: at this scale it is the only evidence there is. The specific open question is whether
`ssuti` (195 documents), `ssutí` (142) and `ssutě` (64) are still scanning errors — appearing in
195 separate documents is not what we would have expected from a scan artefact.

## 5. The archive's register is abbreviated, coded and full of proper nouns — and that breaks dictionary tests

We tested a change that would require a line's words to be attested in the archive's vocabulary
before calling it good. It finds a lot of genuine rubbish — but it destroys **540 lines of
perfectly good text for every 212 it fixes**, and it triples the number of good lines lost.

The expectation was that this would be a language problem: a Czech-centric dictionary convicting
the archive's German. **It is not** — 3% of the destroyed lines carry German markers, 55% carry
Czech ones. What it actually destroys is the archive's characteristic *register*:

```
Bezmírov /s.o. Kroměříž/.              Málek, J., 1966: Vegetační vymezení lesních oblastí…
Věc : Stará Kouřim / Kolín/            větší soubor z eneol.výš.sídliště - publ. Masek, AR IV 1962
Čtverec: 13/14 Sonda: - Jiné: -        NASEZN. 1I/650/7086
sonda/kontext: JZ                      V Hradci Králové, 27.111.1974
J-IXb                                  Dra I.L. Červinky.
```

Site names with administrative qualifiers, form fields, bibliographic citations, inventory codes,
dates, personal names. Median length: three words. **A dictionary has nothing to say about any of
it, and this is the archive's most characteristic and arguably most valuable content** — the part
that makes a find retrievable. Any future proposal of the form "check the words against a word
list" runs into this, and should be measured against it before it is believed.

A related asymmetry worth knowing, because it appears in the annotation files: the dictionary
counts *documents*, not occurrences. `Dauerleihe` appears on 267 lines but in very few documents,
so it counts as unattested. Anything concentrated in a handful of documents — a museum loan
register, a particular form's labels — looks unattested however often it occurs.

## 6. The program currently answers the same string in several ways

Two measurements worth having in mind when reading any per-line quality figure.

**The same text, in one document, answered both ways.** `Mammalia indet.` appears **416 times in a
single document** and is stored as `Trash` 209 times and `Noisy` 207 times. Identical text, same
document, near coin-flip.

**The same organisation, answered three ways depending on typesetting:**

|                           | stored as                                |
|---------------------------|------------------------------------------|
| `ARCHAIA`                 | `Clear` 1,008 · `Trash` 116 · `Noisy` 52 |
| `ARCHAIA Brno o.p.s.`     | `Noisy` 680 · `Trash` 441                |
| `Archaia Brno o.p.s.`     | `Noisy` 359                              |
| `ARCHAIA Olomouc, o.p.s.` | `Noisy` 183 · `Trash` 6                  |

Neither is a scandal — these lines sit near a threshold, and small differences in surrounding
context push them either way. But it is why the annotation request asks about *strings* rather
than lines, and why one answer is allowed to settle many lines at once.

## 7. The finding with the widest consequences: `Trash` is being asked two questions at once

The definitions this project works to are:

* **`Clear`** — no mistakes in the words.
* **`Noisy`** — a human can recognise the meaning through a minor mistake.
* **`Trash`** — nobody can read this.

Measured against those definitions, the current `Trash` bucket does not match. **76.9% of the
flagged `Trash` lines contain no repeated-character run and no unusual glyph at all.** Concretely,
the program currently stores as `Trash`:

* `http://www.arub.cz` — 5,309 lines, read correctly, perfectly legible;
* `e-mail: mhauer@zip-ops.cz` — 181 of its 241 lines;
* `ARCHAIA Brno o.p.s.` — 316 lines, while calling `ARCHAIA` `Clear`.

By the definition above, none of those is `Trash`. Anyone can read them.

What has happened is that one label is answering two different questions:

1. **Can a human read this?** — legibility. That is what the definitions describe.
2. **Is this running text worth keeping and indexing?** — usefulness. A URL, a form label, an
   inventory code and a species name are all perfectly legible and none of them are prose.

The five-category scheme already has a place for the second question — **`Non-text`** — and it is
not being used for it.

**This needs a decision from you two, and it should come before the annotation, not after.** If
the answer is "legibility, as written", then a correctly-scanned URL is `Clear`, the program is
currently mislabelling several thousand lines, and the quality metrics will move when that is
fixed. If the answer is "we want prose and the label is shorthand for that", then the definitions
need rewriting, and `Non-text` is probably where footers, URLs and form labels belong. Either is
workable. What does not work is leaving it implicit: an annotator applying the written definitions
will mark `http://www.arub.cz` as `Clear`, the measured accuracy of the rule will change, and
nobody will be able to tell whether that was the annotator or the definition.

## 7b. Which rules actually protect the readable text, and which destroy it

Added 2026-09-22, after a long measurement (87 hours) finished. It is the first
time we can say what each individual rule does to text **a human called readable**,
rather than what it does to the program's own earlier opinion.

The program applies 23 rules. Switching each one off in turn and re-scoring
against your 2,064 annotated lines gives this:

| rule                       | what it does to lines a human called `Clear` |
|----------------------------|----------------------------------------------|
| the short-line rule        | **protects 31**                              |
| the reference-floor rule   | protects 10                                  |
| **the short-garbage rule** | **destroys 7**                               |
| the hard-sweep rule        | destroys 2                                   |
| two others                 | destroy 1 each                               |

**The third row is the one worth knowing.** The short-garbage rule is the rule
this whole issue has been about — the one your patch narrowed in July. It is
itself responsible for **7 of the 40** readable lines the program currently
loses. The figure of 40 has been the yardstick every decision in this issue is
measured against, and it turns out part of it is produced by the very rule we
have been trying to make safer, rather than being a fixed background cost.

**One caution about the same measurement, because the table it comes from looks
more decisive than it is.** Seven of the 23 rules score *better* when removed. It
is tempting to read that as "delete seven rules". We do not think it is, for a
plain reason: the measurement has no statistical test attached, and five of those
seven move the score by less than a single annotated line out of 2,064. That is
noise, not a finding. Only two move enough to be worth a proper test, and both of
them **cost** readable lines when removed. Nothing here is a reason to remove
anything; we are recording it so that nobody reads the raw table later and
concludes otherwise.

**And one thing the measurement got wrong about itself**, which is worth a
sentence because it concerns the rule at the centre of this issue. The run
reported the new shape-witness rule as *dead code, safe to delete*. It is not
dead — it is switched off, so of course it never fired. The same rule had already
been measured reaching **100,824 lines**. The tool has been fixed so it now says
"switched off" instead of "dead", but it is a fair illustration of why we keep
re-reading these runs rather than trusting their summaries: the instrument
recommended deleting the feature the project has spent two months building.

## 8. What follows from all of this

* **The risk of switching the new rule on is much smaller than the raw numbers suggest**, because
  the archive's own dictionary already protects the abbreviation, the organisation name, the
  species names and the footer URLs. The measurement that shows this is being re-run properly
  before anything is decided.
* **What is left after that is a genuine long tail** — about 9,900 lines across 7,400 different
  strings, 94% of which occur exactly once. That is the part where a human eye is irreplaceable,
  and it is what the re-cut annotation request will sample.
* **Two things cannot be settled by any amount of computation**: whether those eight doubled-letter
  tokens are conventions or errors at full scale (§4), and whether `Trash` means illegible or
  means not-prose (§7).
* **The rule we have been narrowing is part of the cost, not just the fix.** The
  short-garbage rule destroys 7 of the 40 readable lines the program loses; the
  short-line rule saves 31. Both numbers are new, and neither was available
  before the annotations were scored against the rules individually.
* **Automatic quality tests built for prose will keep misfiring on this archive.** Its most
  characteristic text is short, abbreviated, coded and proper-noun-heavy. That is worth stating
  once, plainly, because it will come up again the next time a vocabulary or language-model signal
  is proposed.

---

_Measured 2026-09-21 from the stage-8 delivery, with § 7b added 2026-09-22 from the stage-6 delivery (a 23-rule sweep scored against the 2,064 annotated lines): 113,100 documents, 56,599,631 lines read,
7,493,429 in scope, 100,824 reached by the rule. Every figure here is recomputed from the CSVs
attached to issue #30 and is reproducible from them; the technical write-up is
`agent_dev_logs/digests/30.digest.md` § "Stage 8 read against its own delivery"._
