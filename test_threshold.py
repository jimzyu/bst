"""
Standalone test script for threshold scenario generation.
Runs outside the Streamlit app — no UI, no Google Sheets logging.

By default, generates scenarios informed by the passage's specific diagnosis
(extracted from the summary). Use --no-diagnosis to skip this step.

Requires GEMINI_API_KEY to be set as an environment variable:
    export GEMINI_API_KEY="your-key-here"        # Mac/Linux
    set GEMINI_API_KEY=your-key-here             # Windows

Usage:
    python test_threshold.py --reference "雅各書1:19-27" --count 4 --output results.txt
    python test_threshold.py --reference "雅各書2:14-17" --count 4
    python test_threshold.py --reference "哥林多前書1:18-25" --no-diagnosis
"""

import argparse
import re
import sys
import os
from google import genai
from google.genai import types
from prompts import PromptTemplates

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash"

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY environment variable not set.")
    print("  Mac/Linux:  export GEMINI_API_KEY='your-key-here'")
    print("  Windows:    set GEMINI_API_KEY=your-key-here")
    sys.exit(1)


def extract_diagnosis(summary_text: str) -> str:
    """
    Extract the 經文的診斷 / Passage Diagnosis field from summary output.
    Returns the diagnosis text, or empty string if not found.
    """
    # Try Chinese field first
    ch_pattern = r'\*\*經文的診斷\*\*[：:]\s*(.+?)(?=\n-|\n\[|$)'
    ch_match = re.search(ch_pattern, summary_text, re.DOTALL)
    if ch_match:
        return ch_match.group(1).strip()

    # Try English field
    en_pattern = r'\*\*Passage Diagnosis\*\*[：:]\s*(.+?)(?=\n-|\n\[|$)'
    en_match = re.search(en_pattern, summary_text, re.DOTALL)
    if en_match:
        return en_match.group(1).strip()

    return ""


def generate_summary(client, reference: str) -> tuple:
    """
    Generate passage summary and extract the diagnosis field.
    Returns (summary_text, diagnosis_text).
    """
    prompt = PromptTemplates.get_summary_prompt(reference)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=PromptTemplates.SYSTEM_INSTRUCTION
        )
    )
    summary_text = response.text
    diagnosis = extract_diagnosis(summary_text)
    return summary_text, diagnosis


def generate_scenario(client, reference: str, diagnosis: str = "") -> str:
    """
    Generate one threshold scenario, optionally informed by the diagnosis.
    """
    if diagnosis:
        prompt = "請以繁體中文回應以下所有內容。\n\n" + \
                 PromptTemplates.get_threshold_with_diagnosis_prompt(reference, diagnosis)
    else:
        prompt = "請以繁體中文回應以下所有內容。\n\n" + \
                 PromptTemplates.get_threshold_prompt(reference)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=PromptTemplates.SYSTEM_INSTRUCTION
        )
    )
    text = response.text

    # Extract threshold scenario section
    if "[THRESHOLD_SCENARIO_CHINESE]" in text:
        start = text.find("[THRESHOLD_SCENARIO_CHINESE]")
        return text[start:]
    return text


def run_test(reference: str, count: int, use_diagnosis: bool = True,
             output_file: str = None):
    """
    Generate threshold scenarios for a given reference.

    Args:
        reference: Bible reference
        count: Number of scenarios to generate
        use_diagnosis: Whether to generate summary first and use diagnosis
        output_file: Optional path to save results
    """
    client = genai.Client(api_key=GEMINI_API_KEY)

    print(f"\n{'='*60}")
    print(f"Reference: {reference}")
    print(f"Generating {count} scenario(s) "
          f"{'with diagnosis' if use_diagnosis else 'without diagnosis'}...")
    print(f"{'='*60}\n")

    diagnosis = ""
    if use_diagnosis:
        print("Step 1: Generating passage summary and diagnosis...")
        summary_text, diagnosis = generate_summary(client, reference)
        if diagnosis:
            print(f"\n📋 Passage Diagnosis:\n{diagnosis}\n")
        else:
            print("⚠️  Diagnosis field not found in summary — "
                  "generating scenarios without it.\n")
        print(f"{'='*60}\n")

    results = []
    header = f"Reference: {reference}\n"
    if diagnosis:
        header += f"\nPassage Diagnosis:\n{diagnosis}\n"
    header += f"\n{'='*60}\n\n"

    for i in range(1, count + 1):
        print(f"--- Scenario {i} ---")
        try:
            scenario_text = generate_scenario(client, reference, diagnosis)
            print(scenario_text)
            print()
            results.append(f"=== Scenario {i} ===\n{scenario_text}\n")
        except Exception as e:
            print(f"Error on scenario {i}: {e}")
            results.append(f"=== Scenario {i} ===\nERROR: {e}\n")

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(header)
            f.write("\n".join(results))
        print(f"\nResults saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate threshold scenarios informed by passage diagnosis"
    )
    parser.add_argument(
        "--reference", "-r",
        default="雅各書2:14-17",
        help="Bible reference (default: 雅各書2:14-17)"
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=1,
        help="Number of scenarios to generate (default: 1)"
    )
    parser.add_argument(
        "--no-diagnosis",
        action="store_true",
        help="Skip diagnosis extraction and generate without it"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Optional file path to save results"
    )
    args = parser.parse_args()

    run_test(
        reference=args.reference,
        count=args.count,
        use_diagnosis=not args.no_diagnosis,
        output_file=args.output
    )


if __name__ == "__main__":
    main()
