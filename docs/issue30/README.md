# Issue #30 — what is in this folder

**For:** @DanaKriv and @david-spacil, and anyone joining
[issue #30](https://github.com/ufal/atrium-alto-postprocess/issues/30) without having followed it.

The program in this repository reads the scanned text of the archive line by line and sorts every
line into one of five boxes: `Clear`, `Noisy`, `Trash`, `Non-text`, `Empty`. Issue #30 is about one
change to how it decides. This folder holds everything written for the people who provide the data
and use the results, rather than for the people writing the code.

---

## Read in this order

**1. Start here — what the archive looks like to the program**
[`issue30_corpus_profile.md`](issue30_corpus_profile.md) · for both of you · about 15 minutes

Measured across all 113,100 documents. It covers the two collections, why documents from 2010
onwards behave differently, Latin species names, your own company name in page headers, and why
dictionary-style checks keep misfiring on this archive. Sections 0 and 3 were rewritten on
2026-09-22 after the measurement was repeated correctly; § 3c explains why a correctly scanned
German word is the largest thing at risk. **Nothing in it asks you for anything.** If you read one
document, read this one.

**2a. If you are @DanaKriv — how the labelling works**
[`issue30_annotation_guide.md`](issue30_annotation_guide.md) · about two to four hours of work

What each of the five labels means, what to fill in, what to leave alone, and where to start.
**The earlier notice asking you to wait has been withdrawn** — the files were rebuilt and the
request is ready. Section 7.2 contains a question you can answer without the files, and it is
worth reading before you begin.

**2b. If you are @david-spacil — the open questions**
[`issue30_review_request.md`](issue30_review_request.md) · most items need one line each

Eight items. Item 6, about what `Trash` is for, is the one that matters most and is a question for
the two of you together. Item 4, about eight doubled-letter spellings, no longer holds anything up:
none of the eight can reach the new rule at all, so it has become a question about a safeguard
rather than about the archive. Item 7 is new — a single setting that decides most of what the new
rule would discard.

**3. Reference, when you need it**
[`annotation_ask_README.md`](annotation_ask_README.md) — how the two request files are built and
how to fill them in. Read it together with the guide rather than on its own.

---

## The data files here

| file         | what it is                                                                                                                                                                     |
|--------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `census.csv` | 157 rows. The most common text at risk, every string the program currently answers in two different ways, and 39 checks. **Ready to work on.**                                 |
| `sample.csv` | 200 rows. A random selection from the long tail of rare text. Ready to work on.                                                                                                |
| `frame.json` | A small technical file recording how `sample.csv` was chosen. **It must come back with the answers**, or those 200 rows cannot be turned into a figure. Please do not edit it. |

In `census.csv` and `sample.csv` there are three empty columns: `gold_categ`, `confidence` and
`note`. Those are the ones to fill in. Everything else is there to help you decide.

---

## Files elsewhere in the repository

| where                                       | what it is                                                                                                                                                                                                                                                                     | worth opening?                                                                                                                                        |
|---------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| `data_samples/`                             | Small demonstration files showing every stage of the pipeline. **Important: this data is invented.** An imaginary site, imaginary researchers, no real records from either collection. It exists so anyone can see the shapes of the files without access to the real archive. | Yes — `data_samples/README.md` first, then `DOC_LINE_CATEG/CTX000000002.csv`, which is one row per line of text with the category the program gave it |
| `tools/gold/sidecars/issue30_gold_2067.csv` | The 2,067 lines that have been labelled by hand — your own work, collected into one file. Every accuracy figure quoted in issue #30 is measured against it.                                                                                                                    | It has no text column, so it is hard to read directly. `tools/gold/GOLD.md` explains what it is for                                                   |
| `tools/gold/GOLD_CLEAR.csv`                 | Nine example lines that must always come out as `Clear`. A one-screen illustration of what a labelled row looks like.                                                                                                                                                          | Yes, as an example                                                                                                                                    |
| `README.md` (repository root)               | Mostly installation and configuration. The useful part for you is the five-category table, roughly a third of the way down.                                                                                                                                                    | That table only                                                                                                                                       |
| `docs/categorization_logic.md`              | The full rule-by-rule description of how a line's category is decided. Accurate and complete, but written for developers.                                                                                                                                                      | Only if you want the detail                                                                                                                           |
| `issue30_gold_ab_findings.md` (this folder) | Technical findings from the measurement runs.                                                                                                                                                                                                                                  | Developers only                                                                                                                                       |
| `agent_dev_logs/digests/30.digest.md`       | The complete working record of issue #30, including every correction we have had to make to our own conclusions. Long, and written for us rather than for you — but nothing is hidden in it.                                                                                   | Only if you want the reasoning                                                                                                                        |

**Two notes on licensing**, because they differ. The code is under the MIT licence. The
demonstration data in `data_samples/` is under Creative Commons BY-NC 4.0, which does not allow
commercial reuse. Neither covers the real archive collections.

**One warning about file names.** `data_samples/arup_page_stats_SHORT.csv` and
`arub_page_stats_SHORT.csv` are named after the two collections, but they contain neither. They are
identical to each other and hold only the invented demonstration rows.

---

## The two open questions

Both need a human answer. Neither can be settled by more computing.

**1. What should `Trash` mean?** `http://www.arub.cz` appears on 5,309 lines, scanned perfectly
correctly. The program used to call it `Trash`; since we taught it to recognise web addresses it
calls it `Noisy`, which means *readable through a minor mistake* — and there is no mistake. One
label is being asked two different questions: *can a person read this*, and *is this worth keeping
as text*. The five categories are described in two places that do not agree with each other. The
labelling can start before this is settled, but the answers cannot be scored until it is. See
`issue30_annotation_guide.md` § 7.2 and `issue30_review_request.md` § 6.

**2. Is the new rule set one notch too tight?** The largest single item it would discard is
`Dauerleihe` — German for *permanent loan* — on 286 lines that are scanned correctly. It is caught
by a test for three vowels in a row. Requiring four instead would spare it, and every other
correctly-read item on the list, while still catching the page-stamp marks the rule exists for. We
have measured the trade but not yet checked it against hand-labelled text. See
`issue30_review_request.md` § 7.

---

_If anything here is unclear, or a row is impossible to judge without seeing the page it came from,
please say so rather than working around it. We can send the surrounding lines for any row._
