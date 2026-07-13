# SKILL_BST.md — BST-Specific Implementation Reference

**Read SKILLS.md first.** This document covers only what is specific to BST — the two-layer lesson plan format, misreading preamble, and scenario generation. Framework content, evaluation principles, and house style are shared and live in SKILLS.md.

**Canonical location:** `jimzyu/bst` repo, alongside a synced copy of `SKILLS.md`.

---

## 1. Architecture — Batch Generation, Not Conversation

BST reads a passage and generates content across multiple dimensions simultaneously — summaries, question sets, scenarios — with no interaction with a learner. This is structurally a facilitator-preparation tool, not a learning tool. Do not try to graft conversational capability onto it; that's what BLT is for.

**Two generation modes exist in the codebase:**
1. **Legacy three-set format** (`EMPHASIS_EXPLORE` / `EMPHASIS_UNDERSTAND` / `EMPHASIS_APPLY` templates) — each independently generates observation/interpretation/application questions. Known limitation: thematic convergence — all three sets tend to circle the same territory, with the facilitator expected to pick one. Explore questions are consistently the weakest of the three sets (tend toward content-extraction rather than diagnostic depth).
2. **Two-layer lesson plan format** (`LESSON_PLAN_TEMPLATE`, implemented 2026-06-30) — the current recommended default. Produces one consolidated document rather than three parallel sets requiring manual reconciliation. See §2.

---

## 2. Two-Layer Lesson Plan Format

**Prompt:** `LESSON_PLAN_TEMPLATE` in `prompts.py`. **Method:** `PromptTemplates.get_lesson_plan_prompt(reference)`.
**Parser:** `LessonPlanParser` in `parsers.py` — tag-based extraction using four exact tags:
`[LESSON_PLAN_LAYER1_CHINESE]`, `[LESSON_PLAN_LAYER1_ENGLISH]`, `[LESSON_PLAN_LAYER2_CHINESE]`, `[LESSON_PLAN_LAYER2_ENGLISH]`
**UI:** `display_lesson_plan_interface()` in `study.py` — radio toggle between "🔒 引導者備課資料 Facilitator Guide" and "📄 學員材料 Learner Materials" views, each with trilingual tabs (Traditional/Simplified/English).

**Internal generation sequence (5 steps, private — not in output):**
A. Identify genre. B. Identify central claim. C. Identify 2-4 structural divisions with short descriptive (not interpretive) labels. D. Identify 2-3 misreadings. E. Identify key historical background. F. Formulate the ONE orienting question (becomes 一句定位).

**Layer 1 (Facilitator Guide) sections:** 引言, 經文分段, 討論引導備注 (per-question notes — what to listen for / redirects / optional enrichment), 參考資料, 歸納總意 (ends on an open question, never a tidy summary), 時間分配建議 (table format, targets 100 minutes for a 1.5hr session with 10min buffer).

**Layer 2 (Learner Materials) sections:** 一句定位 (ONE sentence — orients without pre-interpreting, see SKILLS.md §3 test), 生活分享/破冰討論 (2 icebreakers, opens from life experience not the text), 討論問題 (6-8 total: 2-3 observation + 2-3 interpretation + 2 application, arc across the whole passage not converging on one section).

**Quality benchmark:** first tested output (Mark 8:31-9:1, 2026-06-30) scored 9/10. Strongest elements were the 討論引導備注 (facilitator notes) — described as better practical facilitator wisdom than raw question sets typically produce. Minor weakness: facilitator hints embedded in learner-facing questions were sometimes slightly more directive ("不要急著解釋，先把所有動詞找出來") than ideal — should point attention, not prescribe method.

---

## 2A. One-Pass Question Bank (implemented and validated 2026-07-08 — now the most mature generation mode)

**What it replaces:** the legacy three-set format's core weakness — three independent, uncoordinated generation calls that inevitably duplicate territory (confirmed across many test passages: observation questions asking about the same verses, interpretation questions restating each other). The one-pass bank generates ONE pass over the whole passage with the whole emerging question set in view simultaneously, eliminating overlap by construction rather than by patching after the fact.

**Prompt:** `QUESTION_BANK_TEMPLATE` in `prompts.py`. **Method:** `PromptTemplates.get_question_bank_prompt(reference)`.
**System override required:** `PromptTemplates.QUESTION_BANK_SYSTEM` — do NOT call with the default system prompt, which mandates a `[META_ASSESSMENT]` confidence-score block (see §3A below) that has no place in this format. Always pass `system_override=PromptTemplates.QUESTION_BANK_SYSTEM`.
**Parser:** `QuestionBankParser` in `parsers.py` — regex-based extraction of `[V.<verse spec>] [<level>] <question>` tags, groups multiple questions sharing one verse range together (same-range stacking), pairs Chinese/English by position. Provides both a grouped structure (`parse()`) and a flat ordered list (`flat_list()`).
**UI:** `display_question_bank_interface()` in `study.py` — groups questions by verse range with colour-coded level badges (觀察 blue / 詮釋 purple / 應用 green), trilingual toggle, raw output kept in a collapsed debug expander. Button: "📚 問題庫 Question Bank" — coexists with, does not replace, the Lesson Plan and legacy Start Study buttons.

**Internal generation sequence (Step 1, private):**
A. Identify genre. B. Identify central claim. **C. Scan for 8 key textual features** (對比/映襯, 重複詞句, 主要連接詞, 因果關係, 遞進觀念, 神學觀念/鑰字, 命令/應許, 情節高潮 — narrative only), noting which verses each occurs in. **C2. Map theological density** — divide the passage into natural sub-units, rate each HIGH or LOW density. MANDATORY explicit check of the passage's opening and closing verses specifically (these frequently carry title/thesis weight easily missed when a more visually active scene draws attention elsewhere). **D.** Identify 2-3 misreadings (retained from legacy format). **E. Scan for relationships BETWEEN units** (not just within) — see §2B. **F.** Map the full question bank before writing, cross-checked against the density map (every HIGH unit gets ≥1 question) and the non-overlap constraint.

**Governing constraint — read exactly, it has two halves:** avoid asking about the SAME feature twice (redundant focus); but the SAME verse range MAY legitimately receive multiple questions at different levels when the range genuinely supports more than one angle ("same-range depth/stacking") — this is depth, not overlap. Test: would a learner who fully answered the first question still discover something genuinely new from the second? If yes, keep both.

**No fixed question count.** Count emerges from TWO independent sources: (a) the density map — one question per HIGH unit minimum, more with stacking; (b) the inter-unit relationship scan (§2B) — one question PER genuine relationship found. A rich, interlocking passage should produce more questions than a thin one; do not pad or compress to hit a number. (Historical note: an earlier "8-12 questions" fixed target was tested and found to exert more pull than the qualitative guidance beside it — removed entirely in favour of density-driven count.)

**Verse tag format:** `[V.21-28]` for single-chapter passages (no chapter number). `[V.1:21-28]` (colon, no space after "V.") for any passage spanning multiple chapters — decide once per bank, apply to EVERY tag in that bank, never mix notations within one bank. Non-contiguous references allowed: `[V.24, 26, 28]`, `[V.1, 6-7]`.

**Validation record:** 6 initial passages (Mark 1, Romans 1, Mark 2, Romans 2, Isaiah 40, Psalm 23) validated META_ASSESSMENT suppression, same-range depth, non-contiguous tags. 8 further passages (8-57 verses) validated density-driven count and opening/closing coverage — the specific bug that motivated the density-mapping feature (a full Mark 1:1-45 bank skipping v.1-6, the Gospel's own title/thesis material, in one of three regenerations) did not recur across this sample. Multiple rounds on Mark 1:16-2:17 plus new tests on James 4:11-5:6 and 2 Cor 5:11-6:10 validated the inter-unit relationship feature (§2B) including genre generalisation beyond narrative. **Status: mature, considered production-ready as of 2026-07-08.** Full round-by-round history in NOTES.md — read it before modifying this template further, several plausible-sounding changes were tried and reverted or refined based on real output.

---

## 2B. Inter-Unit Structural Relationships (Step 1E of the one-pass bank)

**What it does:** for passages with multiple units, scans for relationships BETWEEN units (not just within one) — lifting the learner's eyes from individual scenes to the passage's larger architecture. Produces a dedicated question using a combined verse tag, e.g. `[V.1:16-20, 2:13-17]`.

**IMPORTANT — this is NOT new framework content.** All four categories checked are pre-existing Step 3 labels (18-39), absorbed and implemented months before this feature — the only thing new is applying them at MACRO (whole-unit-to-whole-unit) scale rather than only the micro (sentence/clause) scale Step 3 was originally implemented at. Do not describe future findings in this area as "new categories" without first checking against the existing 39-label taxonomy in SKILLS.md §1 — this exact mistake was made and corrected once already (see NOTES.md 2026-07-08, "IMPORTANT CORRECTION on category sourcing").

**The four categories, with their label numbers:**
- **循環關係** (label 36, inclusio/bracketing) — opening and closing units mirror each other, framing everything between them.
- **映襯** (label 21, parallelism) — two or more non-adjacent units share an underlying pattern despite different surface content.
- **重複詞句 at macro scale** (label 23) — a word/phrase/term recurring across different (not just within one) unit.
- **遞進觀念 at macro scale** (label 28, escalation) — the strongest and preferred pattern when present: a claim that doesn't just repeat but INTENSIFIES between two units (e.g. authority over demons → authority to forgive sins). Produces the sharpest inter-unit questions per direct comparison testing — prefer this category when a genuine instance exists.

**Critical rules, each added after a specific real bug:**
1. **Check ALL unit pairs, don't stop at the first found** (esp. the opening/closing pair — most visually obvious, easiest to find first, NOT necessarily the only or best relationship present). Write ONE question PER genuine relationship found, not one question total for the whole bank. A rich passage may have 2-3 simultaneously (confirmed: Mark 1:16-2:17 surfaced three in one bank after this fix — wilderness-reversal, authority-escalation, calling-inclusio).
2. **Check units regardless of their individual density rating.** Standalone density (§2A step C2) and relational significance are different axes — a unit too thin for its own question can still matter through what it connects to elsewhere. Do not silently narrow the relationship scan to only HIGH-density units.
3. **Ordering:** a combined-tag question sorts by the LATER unit referenced, not the earlier one (the learner must encounter both units before comparing them). Within that later unit's own sequence: unit's own 觀察 → unit's own 詮釋 → the inter-unit question (if this unit is the later member of a pair) → unit's own 應用. (Bug found and fixed 2026-07-08: sorting by the first verse number placed comparison questions before the learner had seen the second unit at all.)
4. **Quality bar for a strong inter-unit question** (extracted from direct comparison of two real outputs, one much stronger than the other): cite exact verse locations of BOTH occurrences; name the specific linking feature directly, don't leave it for the learner to guess; commit to ONE payoff — a second distinct insight belongs in its own separate unit-level question, don't fold it in; for inclusio specifically, ask what the BRACKETING accomplishes for the framed material, not merely whether the two endpoints resemble each other.
5. **Do not force a pattern that isn't there.** Most short passages will have zero or one genuine relationship — that's fine and expected.

**Emergent capability, not explicitly designed:** the mechanism generalises beyond simple pairs on its own — 2 Cor 5:11-6:10 testing produced a genuine three-point escalation chain (`[V.5:11, 5:20, 6:1]`), tracking an intensifying appeal across three separate units, without the prompt ever specifying more than two.

---

## 3. Misreading Preamble (Legacy Format)

`MISREADING_PREAMBLE` — embedded in all three legacy emphasis templates. Before generating questions, the model identifies 2-3 most likely misreadings of the passage from its rhetorical structure (what assumption is each verse arguing against). Questions are then calibrated against these misreadings.

**STEP 1B experiment (central claim addition) — tried and reverted:**
On 2026-06-30, a `STEP 1B — IDENTIFY THE CENTRAL CLAIM` addition (ported from BLT's central-claim pre-step) was added to all three legacy templates, hypothesizing it would sharpen the weak Explore set. Tested across 4 runs on 2 Cor 4:1-15 (the passage used as the calibration example inside the addition itself — a confound worth noting). **Result: reverted.** Full nine-question comparison across all 4 runs showed Version 1 (pre-addition) was better or equal in the large majority of comparisons; the addition changed question *style* (fewer multi-verse integrative questions, more single-verse concept-extraction questions) without net improvement, and in one run introduced a citation error (quoted a verse outside the passage's actual range). **Do not re-attempt this specific port without addressing why it degraded Explore's multi-verse integration — see NOTES.md 2026-06-30 entries for the full 9-question comparison table.**

**Lesson learned (now in SKILLS.md §2 evaluation discipline):** a fix designed for one tool's architecture (BLT's live, incremental conversation) does not necessarily transfer to a different generation architecture (BST's parallel batch generation) even when the underlying principle (orient toward central claim) is sound in the abstract.

---

## 3A. META_ASSESSMENT / Confidence Score — Origin and Correct Scope

**Legitimate feature, NOT a bug to design around when it appears where it belongs.** Two genuine roots: (a) in the legacy emphasis flow's per-answer evaluation loop, a confidence score is attached to the AI's final evaluation of a learner's (evaluated-then-followed-up) answer; (b) BST's quick/deep summary generation separately attaches a confidence score to its own passage-summary output. Both remain intact and unaffected by anything in §2A.

**Where it does NOT belong — and why it kept leaking into the one-pass bank:** `SYSTEM_INSTRUCTION` (the default system prompt applied by `generate_content_quality(prompt)` whenever no override is passed) contains a hard mandate to always include `[META_ASSESSMENT]`. The one-pass bank evaluates no learner answer and generates no summary, so this mandate never applied — but omitting it from the *user-level* prompt alone wasn't enough to suppress it, because it was a *system-level* instruction. Fixed by building a dedicated `QUESTION_BANK_SYSTEM` override (§2A) — the same pattern already established for scenario generation (`system_override=client.SCENARIO_SYSTEM`). **Rule for any future new generation mode:** if it doesn't fit the legacy evaluate/summarize pattern, give it its own system override rather than assuming the default `SYSTEM_INSTRUCTION` is neutral.

---

## 4. Scenario Generation

**Passage-specificity test** (the single most useful scenario quality criterion identified so far): *a scenario correctly illustrates this passage's misreading if and only if removing this specific passage would make the scenario's self-deception invisible.* If the scenario would work equally well paired with a different passage, it's too generic — revise.

**Gold-standard examples on file** (2 Cor 5:11-6:10 development cycle, per NOTES.md): scenarios that named a specific, observable behavioral detail (e.g., a character deleting an application file from their desktop) rather than only describing an internal state, and that ended on a memorable diagnostic line the group would carry out of the room, scored highest.

---

## 5. What Was Deliberately NOT Implemented / Reverted

- **STEP 1B port from BLT** — see §3. Reverted after 4-run comparison.
- **BST growing its own interactive answer/evaluate/follow-up engine — deliberately rejected, but NOT because BST-adjacent interactivity is categorically out of scope.** (Correction to an earlier, overly broad version of this note.) The actual decision (see NOTES.md 2026-07-08, "BST-to-BLT Handoff — Future Architecture Vision"): BST stays a generation-only tool and does NOT duplicate BLT's conversational machinery — but a *student-facing* use case is explicitly planned: a student browses BST's one-pass question bank (§2A) and picks a question, which hands off into BLT's existing "🔍 追問一個問題" (Option 3) flow, pre-filled with the picked question. This reuses BLT's already-hardened conversational engine rather than rebuilding a second one. Refinement: only 觀察/詮釋-level questions from the bank are planned as clickable entry points; 應用-level questions are displayed as non-clickable "things to ponder" reference material, since an application question answered without prior observation/interpretation reproduces the shallow-application failure pattern already documented in BLT session evaluations. **Status: vision fully documented, implementation NOT yet started** — depends on (a) the one-pass bank being validated (✓ done, §2A) and (b) BLT's Option 3 remaining stable (✓ already is). Not urgent; a well-scoped future piece of work once picked up.
- **Merging the three-set legacy format, the two-layer format, and the one-pass format into one** — all three currently coexist in the codebase. The one-pass format (§2A) is the most mature and recommended default for new work; the two-layer format remains valid for its original use case; the legacy three-set format is not being actively deprecated/removed without further evaluation.

---

*Last updated: 2026-07-11 (was 2026-07-07 — updated to add the one-pass question bank redesign, §2A/§2B, the META_ASSESSMENT scoping note §3A, and to correct the overly broad "BST interactivity out of scope" claim in §5). See NOTES.md for the full round-by-round development history behind every claim in §2A/§2B.*
