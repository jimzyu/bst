📖 Bible Study Tool

An advanced AI research assistant designed for deep scriptural engagement, utilizing Google Gemini-2.0-Flash to provide structured study guides, historical context, and theological synthesis.

🔄 The Evolution: From Theme Tool to Study Partner

This application has transitioned from a basic "summary generator" into a comprehensive Inductive Study Assistant. Key architectural shifts include:

Inductive Methodology: Instead of jumping straight to answers, the tool now generates Observation, Interpretation, and Application questions to guide the user's personal discovery.

Progressive Reveal UI: To encourage active study, the final theological summary is now hidden behind a "View Theme Summary" expander, preventing users from bypassing the reflection process.

Reference Validation (The Gatekeeper): A new validation layer ensures the tool remains a specialized Bible aid by rejecting non-scriptural inputs like "Chicken Soup" or general trivia.

✨ Key Features

🔍 Deep Study Mode (Multi-Draft Synthesis)

When enabled, this mode conducts a rigorous analysis process:

Draft 1: Generates a standard balanced evangelical view.

Draft 2: Focuses exclusively on deep historical, cultural, and linguistic context.

Draft 3: Focuses on practical modern-day life applications.

The Merger: A final AI "Expert Editor" pass combines the best insights from all three drafts into one "Master Version".

🌍 Multi-Language Synchronization

Maintains 100% semantic consistency across three versions:

Traditional Chinese: Precise academic and theological terminology.

Simplified Chinese: Locally converted using OpenCC, with a custom multi-header detection system to ensure the UI Expanders work perfectly.

English: An exact translation of the Chinese content, ideal for cross-linguistic teaching.

🚀 How to Use

Input Reference: Enter a scriptural reference (e.g., Matthew 14:1-36 or Isaiah 53:1-5).

Toggle Mode: Select "Deep Study Mode" for a comprehensive 3-draft synthesis or stay in standard mode for a quick single-shot analysis.

Reflect: Use the "Reflections & Summary" section to answer the generated questions.

Reveal: Click the "📖 查看主題摘要 (View Theme Summary)" expander to see the consolidated theological and historical analysis.

🛠️ Technical Info & Setup

**Requirements

To run this tool locally, install the following:

Bash

pip install streamlit google-generativeai opencc-python-reimplemented

**Environment Settings

Model: gemini-2.5-flash.

Temperature: 0.3 (Set lower to ensure deterministic, consistent, and valid theological results).

Secrets: Add your GEMINI_API_KEY to the Streamlit Advanced Settings (or secrets.toml locally).

**Parsing Logic

The tool uses advanced Regular Expressions (Regex) to extract content safely, ensuring that variations in AI formatting do not crash the application.

📊 Quota & Limits

Daily Quota: Limited to 20 requests per day (resets daily at 12:00 AM PT).

Deep Mode Performance: Deep Study Mode performs 4 internal API calls (3 drafts + 1 merger). Please allow 15-20 seconds for processing.


