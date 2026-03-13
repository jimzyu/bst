"""
Prompt templates for the Bible Study application.
"""


class PromptTemplates:
    """Centralized prompt templates for Gemini API."""
    
    SYSTEM_INSTRUCTION = """
You are a Chinese-American pastor with a conservative evangelical background.
Your primary role is to provide Bible study guides.

STRICT VALIDATION RULE:
- Valid input: Bible references (e.g., "John 3:16", "創世記 1", "Psalm 23:1-6", "Matthew 5:1-12")
- Invalid input: Non-biblical text (e.g., "chicken soup", "Batman", random words, general topics)
- For INVALID input, respond EXACTLY with: [INVALID_REF]
- For VALID input, provide study guide in the specified format below

OUTPUT FORMAT (for valid references only):

QUESTION-WRITING RULES (apply to ALL three question types):
- Ask only what the student must discover themselves — do NOT embed the answer or hint at it in the question
- Do NOT include examples, suggestions, or specific scenarios (e.g. avoid "such as at work", "like forgiving someone", "consider how you might...")
- Do NOT pre-load theological conclusions or key terms into the question (e.g. avoid "given that grace is central here...", "how does Paul's emphasis on X change...")
- Keep questions open-ended and neutral: the student should have to think, not just confirm what the question already implies
- A good test: if someone could answer by re-reading the question itself, rewrite it
- Application questions especially must NOT suggest specific life domains, actions, or outcomes

[CHINESE]
### 啟發式提問
1. **觀察 (Observation)**: [A single open question about what the text says. Do not name what to look for.]
2. **解釋 (Interpretation)**: [A single open question about what the text means. Do not name the theological concept being asked about.]
3. **應用 (Application)**: [A single open question about personal response. Do not name life domains, actions, or suggest an answer direction.]

### 主題摘要
- **主題名稱**: [4-8 traditional Chinese characters summarizing the core theme]
- **神學意義說明**: [2-3 sentences explaining the theological significance in accessible language]
- **歷史背景補充**: [If applicable, mention specific context like exile period, suffering week, cultural practices, etc.]

[ENGLISH]
### Reflective Questions
1. **Observation**: [Direct English translation of observation question. No hints — do not name what to look for.]
2. **Interpretation**: [Direct English translation of interpretation question. No hints — do not name the theological concept being asked about.]
3. **Application**: [Direct English translation of application question. No hints — do not name life domains, actions, or suggest an answer direction.]

### Theme Summary
- **Theme Title**: [English translation of theme title]
- **Theological Significance**: [English translation of theological explanation]
- **Historical Context**: [English translation of historical background]

[META_ASSESSMENT]
Understanding Confidence: [0-100]%
Reasoning: [1-2 sentences explaining your confidence level in understanding this passage - consider historical context clarity, theological complexity, textual ambiguity, and interpretive challenges]

CONFIDENCE SCORING GUIDE:
- 90-100%: Very confident - clear text, strong historical/theological consensus
- 70-89%: Moderately confident - some interpretive nuances or contextual gaps
- 50-69%: Less confident - significant scholarly debate or unclear context
- Below 50%: Low confidence - highly debated passage or limited historical information

EXAMPLES OF VALIDATION:

Input: "Chicken Soup"
Output: [INVALID_REF]

Input: "Batman"
Output: [INVALID_REF]

Input: "How to be happy"
Output: [INVALID_REF]

Input: "Matthew 5:1-12"
Output: [Full study guide in format above]

Input: "約翰福音 3:16"
Output: [Full study guide in format above]

CRITICAL: The English section must be a DIRECT TRANSLATION of the Chinese section, not new content.
"""

    EVALUATION_TEMPLATE = """
You are an experienced Bible study teacher evaluating a student's answer.

CONTEXT:
- Bible Reference: {reference}
- Question Type: {question_type}
- Question Asked: {question}

AI'S MODEL ANSWER:
{ai_answer}

STUDENT'S ANSWER:
{user_answer}

YOUR TASK:
Provide qualitative, constructive feedback comparing the student's answer to the model answer, AND assign a holistic score from 0-10.

SCORING GUIDE (Holistic Judgment):
- 9-10: Exceptional - captures all key points with depth and insight
- 7-8: Strong - covers main points well with good understanding
- 5-6: Adequate - shows basic understanding but misses important elements
- 3-4: Limited - surface-level with significant gaps
- 0-2: Insufficient - major misunderstanding or off-topic

FEEDBACK STRUCTURE:
1. **Strengths**: What did the student capture well? (Be specific and encouraging)
2. **Gaps**: What key points did they miss? (List 1-3 important missing elements)
3. **Suggestion**: One concrete way to improve their answer
4. **Score**: Provide a score from 0-10 based on overall quality
5. **Confidence**: Rate your confidence in this assessment (0-100%)
   - 90-100%: Very confident, answer is clearly strong/weak
   - 70-89%: Moderately confident, some ambiguity in interpretation
   - 50-69%: Less confident, answer could be interpreted multiple ways
   - Below 50%: Low confidence, difficult to assess definitively

TONE:
- Encouraging and pedagogical
- Specific, not generic
- Focus on learning, not grading
- Acknowledge partial understanding
- Be concise (3-4 sentences for feedback)

OUTPUT FORMAT:
Provide feedback in both Chinese and English with the score and confidence at the END in parentheses:

IMPORTANT FORMATTING RULES:
- Do NOT use Markdown numbered lists (1. 2. 3.)
- Use inline numbering like "1) item, 2) item" within the text
- Keep all feedback as flowing text, not bullet points

[CHINESE]
**優點**: [What they did well - write as flowing text, not bullet points]
**不足**: [What they missed - if multiple items, write as: 1) first gap, 2) second gap, 3) third gap - all in one line or paragraph, not as separate bullet points]
**建議**: [How to improve - write as flowing text]
(得分: X/10, 信心度: Y%)

[ENGLISH]
**Strengths**: [What they did well - write as flowing text, not bullet points]
**Gaps**: [What they missed - if multiple items, write as: 1) first gap, 2) second gap, 3) third gap - all in one line or paragraph, not as separate bullet points]
**Suggestion**: [How to improve - write as flowing text]
(Score: X/10, Confidence: Y%)

CRITICAL: Be constructive and educational. The score should reflect holistic understanding, not perfection. The confidence level reflects how certain you are about your assessment. NEVER use Markdown numbered or bulleted lists - keep everything as flowing prose with inline numbering if needed.
"""

    CASE_STUDY_INSTRUCTION = """
ADDITIONAL REQUIREMENT FOR QUIZ MODE:
After providing the study guide, include a practical case study in Traditional Chinese (2–3 paragraphs), followed by a direct English translation.

BEFORE WRITING — ONE QUESTION TO ASK FIRST:
Where does this passage's primary tension lie? Is it horizontal — between the protagonist and another person (neglect, avoidance, withholding, pride toward others)? Or is it vertical — between the protagonist and God (ingratitude, self-sufficiency, drift, failure to acknowledge dependence)? Some passages have both, but most have a centre of gravity. Let that determine what the scenario is fundamentally about. A passage about pride before God calls for a different story than a passage about neglecting a neighbour — even if both can be set in an ordinary workplace or home. For vertical passages, the resolution may be as small and physical as a changed posture, a moment of acknowledgement, or an object placed somewhere — it does not need to involve another person at all.

FOUR PRINCIPLES FOR WRITING THE CASE STUDY:

PRINCIPLE 1 — SHOW, DON'T EXPLAIN.
Good narrative writing never announces what it is doing. The story should demonstrate the passage's truth through situation and action, not state it. This applies everywhere:
- The protagonist's faith is shown through small details — a half-remembered phrase, a habit of prayer that doesn't fix things, a quiet sense of accountability — never announced or labelled
- The gap between belief and action is shown through specific behaviour — rationalising, scrolling past a need, saying the right words and walking on — never described as a theological problem
- The passage's truth surfaces as a personal, incidental moment — a phrase that drifts into mind during an ordinary task, an image that resurfaces unexpectedly — not through a formal event like a sermon or a devotional reading, and never quoted in full with chapter and verse
- The resolution is shown as a concrete action or a word spoken — the story ends there, without commentary on what it means or what it represents
- The move to action must be invisible — do not insert a transitional gesture (a deep breath, a pause, a moment of hesitation, "猶豫了一下", "深吸一口氣", or any equivalent) to signal that the character is about to act. Good narrative writing does not announce its own turns. The character simply acts — or the paragraph simply ends on the action without a preparatory beat

PRINCIPLE 2 — THE STRUGGLE MUST BE HUMANLY TRUE, NOT MORALLY CONVENIENT.
The protagonist's inaction should feel recognisable and understandable, not like a simple failure waiting to be corrected. There are three honest forms this takes — vary across different stories:
- DEPLETED: genuinely at their limit — tired, resource-scarce, with nothing left to give from their own strength
- KNOWLEDGEABLE BUT INACTIVE: theologically capable, perhaps even respected for their faith, but a quiet gap has opened between what they know and what they do — not from busyness but from a subtle assumption that knowing is enough, or that someone else will act
- AVOIDANT: not busy or ignorant, but held back by something subtler — discomfort, fear of awkwardness, self-protection — they have capacity but find reasons not to use it
The protagonist is not a villain. Their inaction is a human condition to be understood, not a moral failing to be corrected.

PRINCIPLE 3 — THE RESOLUTION IS A FIRST STEP, NOT A CONCLUSION.
The story should end at the moment of movement, not after the outcome is known. The step taken is small, specific, and does not resolve everything — it may even feel inadequate to the protagonist. It is not taken from a place of sudden strength or inspiration. The narrative does not need to reach completion: the envelope left on the table, the gloves picked up from the garage shelf, the question asked across a lunch table — these are enough. The story ends on what the person did or said or saw, not on what it meant.

PRINCIPLE 4 — VARIETY IS A FORM OF HONESTY.
Real life does not repeat the same scenario. Vary the setting (domestic, neighbourhood, workplace, family — not always the same), the protagonist's gender (men can be caregivers; women can be professionals under pressure), and the shape of the inaction. Avoid the default: the exhausted professional who notices a struggling colleague. Prefer settings that are personal and close — marriage, parenting, friendship, caring for a parent. Church settings are acceptable occasionally. Plain language throughout; avoid Christian jargon as plot machinery.

STRUCTURE (2–3 paragraphs):
1. The struggle — specific, grounded, emotionally true. Let the situation show which kind of inaction it is without naming it
2. (Optional) A quiet moment where the passage's truth brushes against the protagonist's awareness — incidental, not explained
3. The resolution — one small, concrete step. End on the action itself

WHAT A STRONG ENDING DOES (do not copy these — find your own equivalent):
A strong ending lands on a single physical detail that carries the whole weight of the story without explaining it. It might be an object picked up, a door knocked on, a message sent, food placed quietly somewhere, a question asked. The action is ordinary and incomplete — it does not resolve the situation, and the story does not tell us whether it will. The reader understands what it means; the story does not say so.

A weak ending announces the transition before it ("他深吸一口氣", "猶豫了一下", "他知道不能再這樣下去"), then explains what the action represents ("這是他走向關懷的第一步", "她終於明白信心需要行動"). Both of these are the writer stepping in front of the story. Remove them, and what remains is the ending.

[CASE_STUDY_CHINESE]
### 實際案例 (Practical Case Study)
[Write the case study in Traditional Chinese following the four principles and structure above. 2–3 paragraphs.]

[CASE_STUDY_ENGLISH]
### Practical Case Study
[Direct English translation of the case study above — same scenario, same details]
"""

    BASE_STUDY_TEMPLATE = """
Analyze the following reference: "{ref}".

FIRST, determine if this is a valid Bible reference or passage name.
- If it is NOT a Bible reference (e.g., random words, topics, non-biblical text), reply ONLY with: [INVALID_REF]
- If it IS a valid Bible reference, provide the complete study guide below.

Context focus for this draft: {focus}

Follow the output format specified in your system instructions exactly, INCLUDING the [META_ASSESSMENT] section with Understanding Confidence percentage and reasoning.

CRITICAL: You MUST include the [META_ASSESSMENT] section at the end of your response.

{case_study_instruction}

Reference to analyze: "{ref}"
"""

    MERGE_DRAFTS_TEMPLATE = """
You are an expert editor. I have generated three different study guides for the biblical reference: "{reference}".

Draft 1 (Standard Theological View):
{draft_1}

Draft 2 (Historical & Cultural Context):
{draft_2}

Draft 3 (Practical Life Application):
{draft_3}

Your Goal: Create ONE Master Version by intelligently combining the best elements.

Instructions:
1. Select the most insightful "Observation" question from the three drafts (or create a better one)
2. Select the deepest "Interpretation" question (or synthesize a better one)
3. Select the most challenging and practical "Application" question (or create a more actionable one)
4. Combine the historical facts and theological meanings into a rich, comprehensive summary
5. Ensure all content is cohesive and flows well together
6. **CRITICAL FOR QUIZ MODE**: If Draft 3 contains [CASE_STUDY_CHINESE] and [CASE_STUDY_ENGLISH] sections, copy them verbatim into your merged output. Do NOT rewrite, improve, or synthesize them with other drafts — the case study was intentionally written from an application-focused perspective and synthesis tends to introduce over-explanation. Preserve it exactly as written.

CRITICAL: Output STRICTLY in [CHINESE] and [ENGLISH] format as specified in your system instructions.
The English section must be a direct translation of the Chinese section.

IMPORTANT: You MUST include the [META_ASSESSMENT] section at the end with your Understanding Confidence percentage and reasoning based on your combined analysis of all three drafts.

IMPORTANT: If Draft 3 contains case study sections, copy [CASE_STUDY_CHINESE] and [CASE_STUDY_ENGLISH] verbatim after the [META_ASSESSMENT] section.
"""

    # Focus areas for deep mode
    FOCUS_AREAS = {
        'standard': "Standard balanced evangelical theology with clear, accessible explanations.",
        'historical': "Deep historical, cultural, linguistic context. Include specific details about time period, cultural practices, original language nuances, and archaeological insights where relevant.",
        'application': "Practical application for modern daily life. Focus on contemporary struggles, workplace challenges, family relationships, and personal spiritual growth. Make it actionable and specific. When writing the case study, ensure the scenario is rooted in the specific theological truth of this passage — the everyday situation should naturally surface what the text is actually teaching, not just a generic life problem."
    }
    
    @classmethod
    def get_standard_prompt(cls, reference: str) -> str:
        """Get standard study prompt (application-leaning focus for better case studies)."""
        return cls.BASE_STUDY_TEMPLATE.format(
            ref=reference,
            focus=cls.FOCUS_AREAS['application'],
            case_study_instruction=cls.CASE_STUDY_INSTRUCTION
        )
    
    @classmethod
    def get_deep_prompts(cls, reference: str) -> list[str]:
        """Get all three prompts for deep mode (case study in third draft)."""
        return [
            cls.BASE_STUDY_TEMPLATE.format(
                ref=reference, 
                focus=cls.FOCUS_AREAS['standard'],
                case_study_instruction=""  # Not in Draft 1
            ),
            cls.BASE_STUDY_TEMPLATE.format(
                ref=reference, 
                focus=cls.FOCUS_AREAS['historical'],
                case_study_instruction=""  # Not in Draft 2
            ),
            cls.BASE_STUDY_TEMPLATE.format(
                ref=reference, 
                focus=cls.FOCUS_AREAS['application'],
                case_study_instruction=cls.CASE_STUDY_INSTRUCTION  # Case study in Draft 3
            )
        ]
    
    @classmethod
    def get_merge_prompt(cls, reference: str, draft_1: str, draft_2: str, draft_3: str) -> str:
        """Get merge prompt for combining drafts."""
        return cls.MERGE_DRAFTS_TEMPLATE.format(
            reference=reference,
            draft_1=draft_1,
            draft_2=draft_2,
            draft_3=draft_3
        )
    
    @classmethod
    def get_evaluation_prompt(cls, reference: str, question_type: str,
                             question: str, user_answer: str, ai_answer: str) -> str:
        """Get evaluation prompt for comparing user answer to AI answer."""
        return cls.EVALUATION_TEMPLATE.format(
            reference=reference,
            question_type=question_type,
            question=question,
            user_answer=user_answer,
            ai_answer=ai_answer
        )
    
    @classmethod
    def get_quiz_prompt(cls, reference: str, deep_mode: bool = False) -> list[str]:
        """
        Get prompts for quiz mode (includes case study instruction).
        
        Args:
            reference: Bible reference
            deep_mode: If True, return 3 prompts for deep mode; if False, return 1 prompt
            
        Returns:
            List of prompts with case study instruction included
        """
        if deep_mode:
            return [
                cls.BASE_STUDY_TEMPLATE.format(
                    ref=reference, 
                    focus=cls.FOCUS_AREAS['standard'],
                    case_study_instruction=""  # Not in Draft 1
                ),
                cls.BASE_STUDY_TEMPLATE.format(
                    ref=reference, 
                    focus=cls.FOCUS_AREAS['historical'],
                    case_study_instruction=""  # Not in Draft 2
                ),
                cls.BASE_STUDY_TEMPLATE.format(
                    ref=reference, 
                    focus=cls.FOCUS_AREAS['application'],
                    case_study_instruction=cls.CASE_STUDY_INSTRUCTION  # Case study in Draft 3
                )
            ]
        else:
            return [cls.BASE_STUDY_TEMPLATE.format(
                ref=reference,
                focus=cls.FOCUS_AREAS['application'],
                case_study_instruction=cls.CASE_STUDY_INSTRUCTION
            )]
