# How to help us decide what the text-quality program keeps and throws away

**For:** @DanaKriv, and anyone else reading the archive's scanned text.
**Time needed:** about two to four hours in total. You can stop at any point and send what you have.
**Issue:** [ufal/atrium-alto-postprocess#30](https://github.com/ufal/atrium-alto-postprocess/issues/30)
**Files you need:** `census.csv`, `sample.csv`, `frame.json`

---

## 1. The short version

We have a program that reads the scanned text of the archive line by line and sorts every line
into one of five boxes: **Clear**, **Noisy**, **Trash**, **Non-text** and **Empty**. Lines in
`Trash` are thrown away. Lines in `Clear` are kept as good text.

Earlier this year you pointed out that the program was throwing away far too much. We changed
it, and it now keeps about **367,000 more lines** than before. That fixed your problem, but it
created a smaller one: some real rubbish is now being kept as good text — we estimate about
**26,000 lines**.

We have written a new rule that should catch that rubbish. Before we switch it on, we need to
know one thing: **does it also destroy text that is worth keeping?**

We cannot answer this ourselves. The program can only compare itself against its own earlier
answers, which proves nothing. We need a person who knows the archive to look at the actual
text and say what each line is.

**That is what we are asking you for.** It is 293 decisions.

---

## 2. Why we are asking you and not solving it in code

This is worth one paragraph, because it explains why the request is small and why it is the
only thing that can help.

The new rule can affect **20,078 lines**. Of those lines, **23** currently have a human
opinion attached — about one line in a thousand. Every decision we have made so far therefore
rests on **15 lines** where switching the rule on changes the answer. Fifteen lines is not
enough to decide anything about an archive of 113,100 documents, and no amount of extra
programming changes that number. Only a person looking at text changes it.

---

## 3. What is in the two files

The 20,078 lines are not 20,078 different pieces of text. The archive repeats itself: the same
word appears on printed forms in hundreds of documents. In total there are **4,807 different
pieces of text**, and one of them, `ppole`, appears **11,671 times** on its own.

So we are not asking you to look at lines. We are asking you to look at **each different piece
of text once**. One decision settles every line that contains it.

We have also removed everything where your answer could not change the outcome. Two thirds of
the queue is text the program **already** throws away; the new rule would simply agree with it,
so a label there changes nothing. What is left is **1,584 pieces of text that the program keeps
today and the new rule would start throwing away** — exactly the risk we need measured.

| file          | rows    | what it is                                                                                                                      |
|---------------|--------:|---------------------------------------------------------------------------------------------------------------------------------|
| `census.csv`  | **93**  | The 60 most common of those, plus every piece of text the program currently answers in two different ways. **Start here.**       |
| `sample.csv`  | **200** | A random selection from the long tail of rare text. These are chosen by computer so that we can calculate a result from them.    |
| `frame.json`  | —       | A small technical file. **Please send it back with the others.** Without it the 200 rows cannot be turned into a number.         |

**`census.csv` alone settles 94.8% of the problem.** If you only have time for one file, that
is the one. The 200 rows in `sample.csv` are what let us say something reliable about the rest,
with a stated margin of error, instead of guessing.

---

## 4. What to do

**Fill in the `gold_categ` column. Nothing else.**

Write one of these five words:

| write        | when                                                                                                                                  |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| `Clear`      | This is correct, readable text. A researcher could use it as it stands.                                                                  |
| `Noisy`      | This is damaged, but a person can still tell what it says and it is worth keeping. Use this for text you would not want deleted.         |
| `Trash`      | This is scanning rubbish. Nothing is lost by deleting it.                                                                                |
| `Non-text`   | This is not language at all — a line of a table border, a page decoration, a ruler mark.                                                 |
| `Empty`      | There is nothing here.                                                                                                                   |

**If you are not sure, leave the cell empty.** This is not laziness and it costs us nothing. An
empty cell is skipped completely. A guess is worse than no answer, because we cannot tell the
two apart afterwards and we will build on it. Several of the mistakes in this project came from
somebody filling in a value that looked reasonable.

You may also use the `confidence` and `note` columns for anything you want to tell us. They are
free text and entirely optional. A note saying *"this is an abbreviation used in the 1970s
forms"* is extremely useful to us even when the label itself is obvious.

**Do not change any other column, and do not re-sort or delete rows.** We join your answers back
to the archive using the text in the first column.

---

## 5. The columns, and how to read them

Here is a real row from `census.csv`:

| column             | value                                          | what it means                                                     |
|--------------------|------------------------------------------------|-------------------------------------------------------------------|
| `text`             | `1 fraament okraie`                            | The text to judge.                                                |
| `variants`         | `1 fraament okraie \| 1 .fraament okraie \| …` | Other spellings of the same thing, covered by the same decision.  |
| `lines_settled`    | `558`                                          | Your one answer settles 558 lines of the archive.                 |
| `categ_current`    | `Trash:554\|Clear:3\|Noisy:1`                  | What the program says **today**. Here it disagrees with itself.   |
| `nearest_attested` | `fraament -> fragment (6375, edit1)`           | The closest real word found elsewhere in the archive.             |
| `recoverability`   | `1.00`                                         | How much of the line the archive can reconstruct (0.00 to 1.00).  |
| `clauses`          | `vowel_run`                                    | Which part of the new rule reacted. Technical; you can ignore it. |
| `gold_categ`       | *(empty)*                                      | **Your answer goes here.**                                        |

### About `categ_current`

This is the program's current opinion, and we show it for one reason: where it shows **two
different answers for the same text**, as above, the program is contradicting itself and your
decision resolves that directly. Those rows are all in `census.csv` and are worth doing even if
you do nothing else.

Please **do not** treat `categ_current` as a suggestion. Where it is wrong is exactly what we
are trying to find out, and if the answers simply agree with it we learn nothing.

### About `nearest_attested` and `recoverability`

These come from a dictionary we built out of the archive itself — every word that appears in
several different documents. They are **hints, not conclusions**, and they are unreliable in one
direction in particular:

* A **high** `recoverability` means the archive can reconstruct the words. That is good evidence
  that the line is real text. `1 fraament okraie` is *"1 fragment okraje"*.
* A **zero** `recoverability` means only that **the archive has nothing to say about it**. It is
  *not* evidence of rubbish. `Kaukasus` and `Schuhleistenkeilbruchstueck` both score zero and
  both are perfectly good German archaeological words.
* `edit1` in `nearest_attested` means "one letter different". **This is often a coincidence.**
  `Linum` and `ilium` are one letter apart and both are real Latin words.

And "recoverable" does not mean "damaged". `ppole` can be reconstructed as `pole`, but David has
told us it is an **abbreviation** for *popelnicová pole*, not a scanning error at all. That
correction changed several of our conclusions, which is a good illustration of why we are asking
you rather than measuring harder.

---

## 6. Where to start, and some real rows

Work down `census.csv` from the top. It is sorted so that the most valuable decisions come
first. The first row alone settles 11,671 lines.

Some rows you will meet early:

| text                    |  lines | the program says            | our question                                                              |
|-------------------------|-------:|-----------------------------|---------------------------------------------------------------------------|
| `ppole`                 | 11,671 | `Clear`                     | David says this is an abbreviation. Should it stay `Clear`?               |
| `sektlll`               |    543 | `Clear:539` **`\|Trash:4`** | The program gives the same text two answers. Which is right?              |
| `Triticum monococcum`   |    148 | `Clear`                     | A plant name. We think keeping it is right — please confirm.              |
| `Lepus europaeus`       |     97 | `Clear`                     | An animal name, same question.                                            |
| `f. okraie`             |     76 | `Noisy`                     | Damaged, but is it still useful?                                          |
| `cuxoaid ,`             |     33 | `Clear`                     | We believe this is rubbish being kept. Please confirm.                    |
| `Papaver rhoeas/dubium` |     25 | `Clear`                     | A plant name with a slash. Does that form matter to you?                  |
| `1 fraament okraie`     |    558 | `Trash` (mostly)            | Readable as *"1 fragment okraje"*. Is it worth keeping, or is it rubbish? |

That last one is the question we are least sure about, and it is the mirror image of your
original complaint. There are **690 pieces of text like it** — damaged but readable, currently
being thrown away. Whether a damaged-but-readable line is worth keeping in the archive is a
judgement about what the output is **for**, and it is yours to make, not ours.

---

## 7. Two questions that are not in the files

### 7.1 A policy question about repeated text

The program has a cleaning step that works like this: if the same text appears several times in
one document, all copies are given the **same** answer — whichever answer the majority of them
got.

This means that if the new rule throws away three copies of a word and two copies were correct,
those two correct copies are thrown away as well.

We have measured how often this actually happens in this part of the archive. It is **7 cases,
covering 22 lines**. We have also measured what happens if we turn the cleaning step off: the
new rule makes **more** mistakes, not fewer, and the program loses 15 good lines it is currently
saving.

**Our question:** is losing a small number of correct copies acceptable, when the cleaning step
is, on balance, protecting more than it costs? Or should a bare majority never be allowed to
throw away text that was marked as good?

We are not asking you to decide how to implement it. We are asking which outcome the archive
should prefer. Please answer in one or two sentences.

### 7.2 A re-review we owe you

In July you reviewed a batch of documents with rotated pages and found differences in 95
documents from ARÚP and 10,258 from ARUB. That review compared against the batch we had sent
you, not against a fresh run of the corrected program. We are producing a fresh run now. **You
do not need to do anything yet** — we will send it, and then the question is whether those
differences are still there.

---

## 8. What happens to your answers

1. We join them back to the archive lines, and check the join before we use it.
2. We compare the new rule against your labels and count how many lines it gets **wrong**, not
   how well it scores. (We used a score for a while. It recommended the worst setting we tried.)
3. We decide whether to switch the rule on, and we publish the numbers either way.

**Nothing you write changes the program directly.** No label is applied automatically. If your
answers say the rule is harmful, we do not switch it on — that is the point of asking.

If anything in the files is unclear, or a row is impossible to judge without seeing the page it
came from, please say so rather than working around it. We can send the surrounding lines for
any row.

Thank you — this is the part of the work that nothing else can replace.
