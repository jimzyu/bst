# BST Consolidation Plan

*Drafted 2026-07-14, for review. Companion to NOTES.md, which has the full chronological
log this plan was distilled from — this document is organized by topic and decision,
not by session.*

---

## 1. The problem

BST currently has **at least five independent generation paths** that each re-analyze
the same passage from scratch:

| Path | Template(s) | Re-derives |
|---|---|---|
| Start Study | `EMPHASIS_EXPLORE` / `UNDERSTAND` / `APPLY` | genre, misreadings, 3 questions — **three separate calls per session** |
| Question Bank | `QUESTION_BANK_TEMPLATE` | genre, central claim, density map, inter-unit relationships, misreadings, 8-12 questions |
| Lesson Plan | `LESSON_PLAN_TEMPLATE` | genre, central claim, structural divisions, misreadings, 6-8 questions + facilitator content |
| Summaries | `SUMMARY_TEMPLATE` / `SUMMARY_ENRICHED_TEMPLATE` | theological significance, historical background, diagnosis |
| Scenarios | `PASSAGE_MAPPING_TEMPLATE` → `THRESHOLD_SCENARIO_INSTRUCTION` | verse-anchored claims, diagnosed conditions |

**This was confirmed, not assumed** — evaluated three real outputs for the same passage
(2 Cor 6:11-7:4) side by side. `QUESTION_BANK_TEMPLATE`'s own docstring already names
the specific problem it was built to solve ("three independent, uncoordinated question
sets that inevitably repeat each other's territory") — and Start Study still runs on the
architecture that comment is describing. Its Understand and Apply sets visibly ask
near-duplicate observation and interpretation questions. Separately, Lesson Plan and
Question Bank — generated completely independently — converged on the same inclusio
("sandwich") structural insight. Good evidence the underlying analysis is *stable*; also
proof that two full-price passes are re-deriving the *same* thing.

**Cost is one consequence, but not the only one.** The other is silent inconsistency risk
— five independent passes over the same text could in principle reach different
conclusions about its central claim or structure, and nothing currently guarantees they
won't. They converged this time. There's no reason to expect that every time.

---

## 2. Goal

One shared **core analysis** per passage (genre, central claim, structural divisions,
density map, inter-unit relationships, misreadings — both original-audience and
modern-reader), and one shared **question bank**, generated once. Every other BST feature
consumes and adapts that shared foundation rather than re-deriving it. When the analysis
improves, everything downstream improves with it — the stated aim of today's work: *"when
we continue to improve BST, we just focus on improving the question bank."*

### 2.1 Target end state (added 2026-07-14)

The five current paths collapse to **two consumer surfaces**, both built from the one
shared core analysis:

- **Question Bank** — the individual-study surface. Absorbs Start Study's
  question-generation-and-answering half entirely; Start Study stops being a separate
  pathway and becomes "browse the bank, check what to answer" (see §4). Also carries an
  individual-appropriate view of the core analysis (see §2.2) so a self-study student
  still gets background/context, not just questions.
- **Lesson Plan** — the group-facilitation surface. Absorbs Start Study's
  summary-generation half (theological significance, historical background, diagnosis —
  content that substantially overlaps with what `LESSON_PLAN_TEMPLATE`'s facilitator
  guide already independently produces) and absorbs scenario generation, which is
  inherently a group-discussion technique, conceptually a sibling of icebreakers rather
  than a standalone third feature.

This reframes the whole plan's target from "reduce redundancy across five features" to
"two clearly-scoped surfaces sharing one foundation" — a concrete shape, not just a
direction.

### 2.2 One nuance this raises, to build correctly rather than to reconsider

`LESSON_PLAN_TEMPLATE`'s summary-equivalent content currently lives in Layer 1,
explicitly facilitator-only ("not shown to learners"). Start Study's summary content is
currently learner-facing — an individual student sees it directly today. If summary
generation moves under Lesson Plan naively, an individual self-study student using the
Question Bank surface could lose access to background content they currently get, since
it would sit behind a facilitator-only layer of a feature they're not using.

**Resolution, consistent with the rest of this plan:** the core analysis is generated
once, but produces **two scoped views** — the rich facilitator framing for Lesson Plan's
Layer 1, and a lighter individual-appropriate framing surfaced within the Question Bank
experience — rather than one generation gated behind one audience. Same principle as
everywhere else in this document: single generation, multiple tailored consumption
views.

---

## 3. Staged plan

1. **~~Port step G into `QUESTION_BANK_TEMPLATE`.~~ DONE 2026-07-14.** Turned out to need
   a parser change too, not just a prompt change — `QuestionBankParser`'s regex would have
   shown a `[MISREAD: ...]` tag to the student verbatim without it. New `misread` field
   added to the parsed structure (`None` for the common no-tag case), not yet consumed by
   anything downstream — that's for steps 3-4, where it can hint `EVALUATION_TEMPLATE`'s
   `[PATTERN: ...]` flag for whichever bank question a student actually answers. Also
   corrected an assumption from this plan's original scoping: Question Bank already had
   parity with Lesson Plan's *original-audience* misreading step (its own step D) — the
   real gap was narrower, just the modern-reader half. Not yet tested live.

2. **~~Promote `QUESTION_BANK_TEMPLATE`'s Step 1 to a canonical shared core analysis.~~
   DONE 2026-07-14.** Extracted steps A-E into `CORE_ANALYSIS_TEMPLATE` +
   `get_core_analysis_prompt()`, producing a real, structured, output-format artifact for
   the first time (previously this reasoning existed only inside one call, explicitly
   marked "do not include in output"). Added a consume-mode `QUESTION_BANK_FROM_ANALYSIS_TEMPLATE`
   and a new `CoreAnalysisParser`. `QUESTION_BANK_TEMPLATE` itself is untouched — mechanically
   verified byte-identical, and `get_question_bank_prompt()`'s no-argument path confirmed
   unchanged. A real multi-range parsing bug was caught in testing (not before it) and fixed.
   Not yet wired into `study.py` or any live feature, and not yet tested against a real
   model call — see NOTES.md Pending Tests.

3. **Make the question bank the single source of questions**, generated once per
   passage from that core analysis.

4. **Refactor Lesson Plan and Start Study to consume the shared bank + core analysis**
   rather than regenerate independently. See §4 below — this step has a worked-out design
   for the Start Study side specifically.

5. **Retire Summaries and Scenario Generation as separate paths — absorb them into
   Lesson Plan**, per the target end state in §2.1. Summary content (theological
   significance, historical background, diagnosis) moves into Lesson Plan's Layer 1,
   drawing on the shared core analysis rather than a separate `SUMMARY_TEMPLATE` /
   `SUMMARY_ENRICHED_TEMPLATE` pass. Scenario generation (`PASSAGE_MAPPING_TEMPLATE` →
   `THRESHOLD_SCENARIO_INSTRUCTION`) moves in as a facilitation technique alongside
   icebreakers, grounded in the same core analysis rather than its own independent
   "teaching points" derivation.

**Scope note:** steps 2-5 are a real data-flow refactor — how generation calls feed each
other — not an in-place prompt-language edit like today's other BST changes. Worth
scoping and building deliberately, not folded into a quick pass. Step 1 can be done
immediately and independently of the rest.

---

## 4. Phase 4 in detail: Start Study ↔ Question Bank merge

**Core mechanic:** Start Study stops generating its own three question sets. Instead, the
student browses the already-generated bank and checks which questions they want to
answer — full visibility into the whole passage before committing to any one part of it.

**Addressing "could this be overwhelming":** yes, as a blank slate with no guidance — the
bank's default phrasing register is closer to today's UNDERSTAND tier than EXPLORE's
deliberately gentler style, and 8-12 unweighted questions is real decision fatigue for
someone who just wants to start. Mitigation: **a sensible subset (spanning
觀察/詮釋/應用, similar in size to today's single emphasis set) pre-checked and fully
editable.** A student who wants simplicity accepts the default and starts exactly as
before. A student who wants to browse and choose their own path through the passage gets
that ownership for free — a genuine upgrade in agency, not just a simplification.

**The gap in the original proposal, and its resolution:** collapsing to one bank loses the
implicit link between "emphasis" (Explore/Understand/Apply) and `EVALUATION_TEMPLATE`'s
grading calibration — EXPLORE grades generously and never corrects in tone; UNDERSTAND
presses on reasoning; APPLY refuses to let vagueness pass. That calibration is real,
valuable behavior, not just a phrasing difference in the questions themselves, and a pure
checkbox design would drop it silently. **Agreed resolution: keep emphasis, but decouple
it from question-generation.**

- Emphasis becomes a **session-level toggle** (gentle / analytical / personal), chosen
  once, not three separately generated content sets.
- It feeds `EVALUATION_TEMPLATE`'s existing calibration language regardless of which
  bank questions the student picked.
- It **biases the default checkbox pre-selection** — gentle → 觀察-heavy default;
  personal → 應用-heavy default — so the toggle still shapes the experience, not just
  the grading tone.

This preserves nearly everything the three-set system did — guidance, tone, a sense of
"this fits where I am" — from a single generation pass instead of three.

**Plumbing implication:** `study.py` goes from three separate generation calls down to
one. `EVALUATION_TEMPLATE` / `FOLLOWUP_QUESTION_TEMPLATE` / `REDIRECT_QUESTION_TEMPLATE`
barely change — they already take `emphasis` as a parameter; it just stops being tied to
which of three independently-generated sets produced the question in front of the
student.

---

## 5. What's explicitly NOT changing

- **Lesson Plan's facilitator-only content** (intro essay, reference materials, timing,
  icebreakers, concluding thought) — not questions, wouldn't be replaced by a shared bank.
  Lesson Plan continues to curate a subset of bank questions into its time-boxed
  structure and adds this material on top.
- **`REDIRECT_QUESTION_TEMPLATE` / `FOLLOWUP_QUESTION_TEMPLATE`** — already well-designed
  for the Socratic "point back to text, never signal wrong" job, arrived at independently
  of anything imported from BLT today. No gap found here.
- **`QUESTION_BANK_TEMPLATE`'s own internal logic** (density mapping, non-redundancy
  check, inter-unit scanning) — this is the part being promoted to canonical status, not
  rewritten.
- **Individual students' access to background/context content** — even though summary
  generation moves under Lesson Plan (§2.1), a self-study student using Question Bank
  should not lose the learner-facing summary content Start Study gives them today. See
  §2.2 for how this is preserved (two scoped views, one generation).

**Start Study's fate, stated plainly:** it does not survive as a third top-level pathway.
Its question half becomes Question Bank's browse-and-answer experience (§4). Its summary
half becomes part of Lesson Plan's shared core analysis, surfaced back to individual
students via the scoped view in §2.2.

---

## 6. Open questions before building steps 2-5

- Does the shared core analysis get regenerated per session, or cached/reused across
  sessions for the same passage? (Connects to the prompt-caching / cost-effectiveness
  thread from earlier today — same underlying principle, different layer: caching a
  *generated artifact* for reuse across features, not caching a *system prompt* for
  reuse across turns.)
- For Lesson Plan's curation step (picking 6-8 of the bank's 8-12 questions into a
  100-minute structure) — does this become a lighter selection+sequencing pass once the
  bank already exists, or does it still need its own reasoning about time allocation?
  Likely lighter, but not yet designed in detail.
- Does Start Study's emphasis toggle need a fourth "no preference / default" option, or
  should gentle/analytical/personal always require an explicit choice?

---

## 7. Suggested next step

Step 1 (port step G into `QUESTION_BANK_TEMPLATE`) is ready to build now — contained,
already-proven pattern, no open design questions. Steps 2-5 are agreed in principle but
not yet built; recommend treating them as their own scoped session rather than folding
into a quick pass, given the data-flow changes involved.
