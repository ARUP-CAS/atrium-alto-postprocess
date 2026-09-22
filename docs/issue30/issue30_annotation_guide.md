# How to help us decide what the text-quality program keeps and throws away

**For:** @DanaKriv, and anyone else reading the archive's scanned text.
**Time needed:** about two to four hours in total. You can stop at any point and send what you have.
**Issue:** [ufal/atrium-alto-postprocess#30](https://github.com/ufal/atrium-alto-postprocess/issues/30)
**Files you need:** `census.csv`, `sample.csv`, `frame.json`

---

> ## ⏸️ Please wait before starting — 2026-09-21
>
> **The files currently attached are sized against the wrong population, and we would be wasting
> your time.** We measured the risk with one of the program's own safeguards switched off by
> mistake. With it switched on — which is how the program actually runs — **about three quarters
> of what we were going to ask you about cannot be affected at all**, including the single
> biggest item (`ppole`, 15,466 lines) and most of the rest of the first page.
>
> We are re-cutting the request now. It will be **smaller**, and it will be mostly a random
> sample rather than a list of the most common text, because once the safe items are removed
> there is no "most common" left — 94% of what remains occurs exactly once.
>
> Nothing you may already have done is wasted: the answers still join back. But please do not
> start a fresh session on these files. **Section 7.2 below is a question you can answer right
> now, without the files, and it is currently the most useful thing in this document.**
>
> The full reasoning is in `agent_dev_logs/digests/30.digest.md` § T1 and T2. We are telling you
> in this much detail because this is the third time in this issue that a summary of a run
> turned out not to survive reading the run itself, and you are entitled to know when that
> affects a request we made of you.

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

The new rule can affect **100,824 lines** across the whole archive. Of those lines, a few dozen
currently have a human opinion attached — far less than one line in a thousand. Every decision we
have made so far therefore rests on about **fifteen lines** where switching the rule on changes
the answer. Fifteen lines is not enough to decide anything about an archive of 113,100 documents,
and no amount of extra programming changes that number. Only a person looking at text changes it.

What programming *did* change, in the last few days, is **how many of those 100,824 lines are
genuinely at stake**. The program keeps a dictionary built from the archive's own words, and
anything appearing across enough documents is left alone by the new rule. We had measured the
risk without that dictionary loaded. With it loaded, the number of lines that are both kept today
and threatened by the rule drops from **37,555 to about 9,900**. That is the re-cut described in
the notice above.

---

## 3. What is in the two files

The 100,824 lines are not 100,824 different pieces of text. The archive repeats itself: the same
word appears on printed forms in hundreds of documents. In total there are **50,042 different
pieces of text**, and one of them, `ppole`, appears **15,466 times** on its own.

So we are not asking you to look at lines. We are asking you to look at **each different piece
of text once**. One decision settles every line that contains it.

We have also removed everything where your answer could not change the outcome. Most of the
queue is text the program **already** throws away; the new rule would simply agree with it, so a
label there changes nothing.

| file         |    rows | what it is                                                                                                                    |
|--------------|--------:|-------------------------------------------------------------------------------------------------------------------------------|
| `census.csv` | **592** | The most common at-risk text, plus every piece of text the program currently answers in two different ways.                   |
| `sample.csv` | **200** | A random selection from the long tail of rare text. These are chosen by computer so that we can calculate a result from them. |
| `frame.json` |       — | A small technical file. **Please send it back with the others.** Without it the 200 rows cannot be turned into a number.      |

As delivered, `census.csv` claims to settle 82.8% of the problem in 592 decisions. **That is the
figure the notice at the top of this document withdraws.** Against the text that is really at
risk, it settles about 31%.

The reason is simple. The items that made the list efficient — `ppole`, the `ARCHAIA` company
name, `Lepus europaeus`, `vodovod` — are exactly the ones the dictionary already protects. The re-cut request will be smaller and will lean on `sample.csv`'s method
rather than on a list of the most common text.

---

## 4. What to do

**Fill in the `gold_categ` column. Nothing else.**

Write one of these five words:

| write      | when                                                                                                                             |
|------------|----------------------------------------------------------------------------------------------------------------------------------|
| `Clear`    | This is correct, readable text. A researcher could use it as it stands.                                                          |
| `Noisy`    | This is damaged, but a person can still tell what it says and it is worth keeping. Use this for text you would not want deleted. |
| `Trash`    | This is scanning rubbish. Nothing is lost by deleting it.                                                                        |
| `Non-text` | This is not language at all — a line of a table border, a page decoration, a ruler mark.                                         |
| `Empty`    | There is nothing here.                                                                                                           |

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
  `Linum` and `ilium` are one letter apart and both are real Latin words. We can now put a number
  on how much of the evidence this affects: **90% of all the suggestions in these files are
  `edit1`** (12,511 of 13,972), and they were generated with a setting that our own tooling warns
  is too permissive on an archive this size. The re-cut request will use a stricter setting. Until
  then, treat `nearest_attested` as a prompt to look, never as a reason to agree.

And "recoverable" does not mean "damaged". `ppole` can be reconstructed as `pole`, but David has
told us it is an **abbreviation** for *popelnicová pole*, not a scanning error at all. That
correction changed several of our conclusions, which is a good illustration of why we are asking
you rather than measuring harder.

---

## 6. Where to start, and some real rows

`census.csv` is sorted so that the largest decisions come first — the first row alone covers
15,676 lines. Please read § 7.2 before working down it, and see the notice at the top of this
document about why the re-cut version is worth waiting for.

Some rows you will meet early:

| text                  |  lines | the program says                     | our question                                                              |
|-----------------------|-------:|--------------------------------------|---------------------------------------------------------------------------|
| `ppole`               | 15,676 | `Clear:15,494` `Noisy:180` `Trash:2` | David says this is an abbreviation. Should it stay `Clear`?               |
| `ARCHAIA`             |  1,176 | `Clear:1,008` `Trash:116` `Noisy:52` | Your own company name, answered three ways. Which is right?               |
| `ARCHAIA Brno o.p.s.` |  1,121 | `Noisy:680` `Trash:441`              | The same name with the town — and a different answer.                     |
| `Lepus europaeus`     |    976 | `Clear:955` `Noisy:16` `Trash:5`     | An animal name. We think keeping it is right — please confirm.            |
| `Mammalia indet.`     |    910 | `Trash:472` `Noisy:438`              | Near coin-flip on identical text. Which is right?                         |
| `vodovod`             |    619 | `Clear:331` `Trash:207` `Noisy:81`   | An ordinary Czech word the rule dislikes for its repeated letters.        |
| `1 fraament okraie`   |    530 | `Trash` (mostly)                     | Readable as *"1 fragment okraje"*. Is it worth keeping, or is it rubbish? |
| `Dauerleihe`          |    305 | `Clear:277` `Trash:19` `Noisy:9`     | A real German museum term the archive's dictionary does not know.         |
| `sektlll`             |    543 | `Trash`                              | We believe this is genuine rubbish. Please confirm.                       |

The `1 fraament okraie` row is the question we are least sure about, and it is the mirror image
of your original complaint: damaged but readable, currently being thrown away. Whether a
damaged-but-readable line is worth keeping in the archive is a judgement about what the output is
**for**, and it is yours to make, not ours.

Several rows above are on the list only because the dictionary was switched off when the files
were built. `ppole`, `ARCHAIA`, `Lepus europaeus`, `vodovod` and `Dauerleihe` are all protected
once it is switched on. They are still worth your opinion if you have one. But they are no longer
the risk.

---

## 7. Three questions that are not in the files

### 7.1 A policy question about repeated text

The program has a cleaning step that works like this: if the same text appears several times in
one document, all copies are given the **same** answer — whichever answer the majority of them
got.

This means that if the new rule throws away three copies of a word and two copies were correct,
those two correct copies are thrown away as well.

We have now measured how often this actually happens across **both collections in full**, rather
than in one sample. Of 61,682 groups of repeated text, 61,359 are unanimous and only 323 are
contested at all. The cleaning step pulls **24 good lines down** — and it **rescues 305 lines**
that would otherwise have been thrown away. It is protecting roughly twelve lines for every one
it costs. We have also measured what happens if we turn it off: the new rule makes **more**
mistakes, not fewer.

**Our question:** is losing a small number of correct copies acceptable, when the cleaning step
is, on balance, protecting more than it costs? Or should a bare majority never be allowed to
throw away text that was marked as good?

We are not asking you to decide how to implement it. We are asking which outcome the archive
should prefer. Please answer in one or two sentences.

### 7.2 The question we would most like answered, and it needs no files

This one came out of the full-collection measurement and it may matter more than the labels.

The definitions we work to are:

* **`Clear`** — no mistakes in the words.
* **`Noisy`** — a person can still tell what it says, through a minor mistake.
* **`Trash`** — nobody can read this.

By those definitions, these lines are not `Trash`. Anyone can read them:

* `http://www.arub.cz` — 5,309 lines, scanned perfectly correctly;
* `e-mail: mhauer@zip-ops.cz`;
* `ARCHAIA Brno o.p.s.` — while `ARCHAIA` on its own is marked `Clear`.

The program currently marks all three as `Trash`. And in fact **77% of everything the program
throws away in this part of the archive has nothing wrong with it at all** — no garbled letters,
no strange symbols. It is readable text that simply is not prose: web addresses, form labels,
inventory codes, company names in page headers.

We think one label is being asked two different questions:

1. **Can a person read this?** — which is what the definitions describe; and
2. **Is this running text worth keeping and searching?** — which is a different question, and the
   one the program seems to be answering in practice.

**Our question to you: which of the two do you actually want?**

* If it is *readability*, then a correctly scanned web address is `Clear`, and we should fix the
  program — it is currently discarding several thousand perfectly readable lines.
* If it is *usefulness as text*, then the definitions need rewriting, and there is already a
  category for the second question — **`Non-text`** — which is where footers, URLs and form
  labels would belong.

Either answer is workable and we will do whichever you prefer. What we cannot do is leave it
unsaid. Suppose you start labelling and mark `http://www.arub.cz` as `Clear`. That is the correct
answer under the definitions as written. But the measured accuracy of the new rule will then
change, and we will not be able to tell whether that came from the definition or from the rule.

**A couple of sentences on this would unblock more than the labels will.**

### 7.3 A re-review we owe you

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
