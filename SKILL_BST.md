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

## 3. Misreading Preamble (Legacy Format)

`MISREADING_PREAMBLE` — embedded in all three legacy emphasis templates. Before generating questions, the model identifies 2-3 most likely misreadings of the passage from its rhetorical structure (what assumption is each verse arguing against). Questions are then calibrated against these misreadings.

**STEP 1B experiment (central claim addition) — tried and reverted:**
On 2026-06-30, a `STEP 1B — IDENTIFY THE CENTRAL CLAIM` addition (ported from BLT's central-claim pre-step) was added to all three legacy templates, hypothesizing it would sharpen the weak Explore set. Tested across 4 runs on 2 Cor 4:1-15 (the passage used as the calibration example inside the addition itself — a confound worth noting). **Result: reverted.** Full nine-question comparison across all 4 runs showed Version 1 (pre-addition) was better or equal in the large majority of comparisons; the addition changed question *style* (fewer multi-verse integrative questions, more single-verse concept-extraction questions) without net improvement, and in one run introduced a citation error (quoted a verse outside the passage's actual range). **Do not re-attempt this specific port without addressing why it degraded Explore's multi-verse integration — see NOTES.md 2026-06-30 entries for the full 9-question comparison table.**

**Lesson learned (now in SKILLS.md §2 evaluation discipline):** a fix designed for one tool's architecture (BLT's live, incremental conversation) does not necessarily transfer to a different generation architecture (BST's parallel batch generation) even when the underlying principle (orient toward central claim) is sound in the abstract.

---

## 4. Scenario Generation

**Passage-specificity test** (the single most useful scenario quality criterion identified so far): *a scenario correctly illustrates this passage's misreading if and only if removing this specific passage would make the scenario's self-deception invisible.* If the scenario would work equally well paired with a different passage, it's too generic — revise.

**Gold-standard examples on file** (2 Cor 5:11-6:10 development cycle, per NOTES.md): scenarios that named a specific, observable behavioral detail (e.g., a character deleting an application file from their desktop) rather than only describing an internal state, and that ended on a memorable diagnostic line the group would carry out of the room, scored highest.

---

## 5. What Was Deliberately NOT Implemented / Reverted

- **STEP 1B port from BLT** — see §3. Reverted after 4-run comparison.
- **BST as an interactive/conversational tool** — explicitly out of scope. BST's value is breadth and completeness of preparation material for a facilitator, not conversational responsiveness. If a use case seems to need conversational BST, that's a signal it belongs in BLT instead.
- **Merging the three-set legacy format and two-layer format into one** — currently coexist; the two-layer format is the recommended default going forward but the legacy format is not being deprecated/removed without further evaluation across more passages.

---

*Last updated: 2026-07-07.*
