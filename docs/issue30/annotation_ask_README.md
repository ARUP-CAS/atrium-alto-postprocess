# Issue #30 — the annotation request

> ## ⏸️ Please do not start on these files yet
>
> **They were built from the wrong set of lines, and we are rebuilding them.**
>
> The program keeps a dictionary of words that appear across the archive, and anything in that
> dictionary is left alone by the new rule. When we measured how much text was at risk, that
> dictionary was switched off by mistake. With it switched on, **about three quarters of what we
> were going to ask about cannot be affected at all.**
>
> That includes the single biggest item on the list — `ppole`, 15,466 lines — and most of the rest
> of the first page.
>
> The replacement will be **smaller**. It will also be mostly a random selection rather than a list
> of the most common text, because once the safe items are removed there is no "most common" left:
> 94% of what remains appears exactly once.
>
> **Nothing already done is wasted.** Any answers still join back correctly.
>
> The files below are kept exactly as they were delivered, so the record is complete.

---

## What to do

Fill in **`gold_categ`** only. Write one of: `Clear`, `Noisy`, `Trash`, `Non-text`, `Empty`.

**If you are not sure, leave it blank.** A blank cell is skipped. It is never treated as a guess.

`confidence` and `note` are free text and optional. Please do not change any other column, and do
not re-sort or delete rows.

One row is one decision. The `lines_settled` column shows how many lines of the archive that one
decision settles.

## The two files

| file         | rows |       lines settled | what it is                                                                                                                                |
|--------------|-----:|--------------------:|-------------------------------------------------------------------------------------------------------------------------------------------|
| `census.csv` |  592 |              31,102 | The most common text at risk, plus every string the program currently answers in two different ways. Complete, not a sample.              |
| `sample.csv` |  200 | 9,906 (represented) | A random selection from the long tail of rare text.                                                                                       |
| `frame.json` |    — |                   — | A small technical file. **Please send it back with the answers.** Without it the 200 rows in `sample.csv` cannot be turned into a number. |

## What the request was meant to buy

These were the figures at delivery:

* The full list holds **50,042 different pieces of text**, covering **100,824 lines**.
* Of those, **8,529 pieces of text / 37,555 lines** were thought to be *at risk* — meaning the
  program keeps them today, so switching the new rule on would start discarding them. The rest are
  already discarded, where an answer cannot change anything.
* `census.csv` was expected to settle **82.8%** of that risk in 592 decisions.
* `sample.csv` was expected to estimate the rest to within **±6.9 percentage points**.

**The last two figures do not hold**, for the reason in the notice above. Measured against the way
the program actually runs, the text genuinely at risk is **7,433 pieces / 9,876 lines**, not
8,529 / 37,555. On that smaller set the 592 rows of `census.csv` settle about **31%**, not 82.8%.

A list of the most common text is the right tool for the first set and the wrong tool for the
second. That is why the replacement is being rebuilt as a random selection, rather than by running
the same method again on a new file.

## The selection record — please keep this file with the answers

Without `frame.json`, `sample.csv` cannot be turned into a number and becomes 200 individual
opinions.

`sample.csv` is drawn from three groups. Each row stands for a number of similar rows that were not
included, and `weight` is how many:

| group             | pieces of text | lines | how many we ask about |  weight | margin of error |
|-------------------|---------------:|------:|----------------------:|--------:|----------------:|
| `at_risk/full`    |          3,252 | 4,483 |                    80 |   40.65 |    ±11.0 points |
| `at_risk/none`    |          2,798 | 3,053 |                    69 | 40.5507 |    ±11.8 points |
| `at_risk/partial` |          2,090 | 2,370 |                    51 | 40.9804 |    ±13.7 points |

To turn answers into a figure for the whole archive, we work out a rate for each group separately,
then combine the three by their **line** counts — not by their counts of distinct text. The three
groups have very different average numbers of lines per entry, so combining them the other way
gives the wrong answer.

One shortcut looks right and is not: multiplying `lines_settled` by `weight` gives 10,051 lines
against the 9,906 recorded above. The weight counts pieces of text, not lines.

Settings used to build these files: `--census 60 --sample 200 --seed 30`.

---

Nothing here suggests an answer, and nothing written in these files changes the program directly.
The answers are joined back separately and looked at first.
