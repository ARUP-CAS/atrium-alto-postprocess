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
dictionary-style checks keep misfiring on this archive. **Nothing in it asks you for anything.**
If you read one document, read this one.

**2a. If you are @DanaKriv — how the labelling works**
[`issue30_annotation_guide.md`](issue30_annotation_guide.md) · about two to four hours of work

What each of the five labels means, what to fill in, what to leave alone, and where to start.
**It currently opens with a notice asking you to wait** — please read that first. Section 7.2
contains a question you can answer straight away, without the files, and it is the most useful
thing in the document right now.

**2b. If you are @david-spacil — the open questions**
[`issue30_review_request.md`](issue30_review_request.md) · most items need one line each

Seven items. Item 4, about eight doubled-letter spellings, is the one nobody else can answer:
every automatic method we have tried has now failed. Item 6 is a question for the two of you
together.

**3. Reference, when you need it**
[`annotation_ask_README.md`](annotation_ask_README.md) — how the two request files are built and
how to fill them in. Read it together with the guide rather than on its own.

---

## The data files here

| file         | what it is                                                                                                                                                                     |
|--------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `census.csv` | 592 rows. The most common text at risk, plus every string the program currently answers in two different ways. **On hold** — see the notice in `annotation_ask_README.md`.     |
| `sample.csv` | 200 rows. A random selection from the long tail of rare text. Also on hold.                                                                                                    |
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

**1. What should `Trash` mean?** The program currently marks `http://www.arub.cz` as `Trash` on
5,309 lines. It is scanned perfectly correctly and anyone can read it. One label is being asked two
different questions — *can a person read this*, and *is this worth keeping as text* — and the five
categories are currently described in two places that do not agree with each other. This needs
settling **before** the labelling starts. See `issue30_annotation_guide.md` § 7.2 and
`issue30_review_request.md` § 6.

**2. Are eight doubled-letter spellings scanning errors or abbreviations?** We have tried three
automatic methods. The third one pointed the wrong way: the one confirmed abbreviation looks more
like a scanning error than any real scanning error does. See `issue30_review_request.md` § 4.

---

_If anything here is unclear, or a row is impossible to judge without seeing the page it came from,
please say so rather than working around it. We can send the surrounding lines for any row._
