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

**✅ Answered in full on 2026-09-22.** Eight items, all closed or waiting on @DanaKriv. Worth
reading even though nothing is asked of you any more: two of the answers correct things this folder
used to state as fact — three doubled-letter spellings turn out to be an old spelling of *suť*
rather than scanning errors, and two strings we described as correctly scanned are not.

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

## The two open questions — both now answered by @david-spacil

He answered on 2026-09-22, and neither answer came from more computing. Both are recorded in full
in [`issue30_review_request.md`](issue30_review_request.md).

**1. What should `Trash` mean?** ✅ **Illegible.** Anything legible is `Clear`; easily decipherable
is `Noisy` — regardless of how useful the line is. So a correctly scanned web address such as
`http://www.arub.cz` is `Clear`. `Trash` lines should be scanned again rather than deleted, and
`Non-text` cannot be judged without the page image, so it is out of scope for labelling.

**@DanaKriv, this is the one thing worth reading before you start.** It is his view, not yet a
joint decision, and the whole measurement is scored against it. If you disagree, please say so
first. See `issue30_annotation_guide.md` § 4 and § 7.2.

**2. Is the new rule set one notch too tight?** ✅ **It is set to the wrong question.** The test
looks for three vowels in a row, which is good evidence of damage in Czech — Czech has no
three-vowel runs — and simply wrong for German and French, where words like `Dauerleihe` and
`FEUILLETON` have them naturally. His answer is to split the rule by language rather than blunt it.

He also corrected us: `J. Vysoean` and `POSTKRANIAINY SKELET` are **not** correctly scanned, as we
had written. They are real scanning errors, so the three-vowel test catches them rightly. See
`issue30_review_request.md` § 7.

---

_If anything here is unclear, or a row is impossible to judge without seeing the page it came from,
please say so rather than working around it. We can send the surrounding lines for any row._
