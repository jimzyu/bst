"""
Name and context generator for threshold scenario generation.
Provides randomised Chinese/English names and scenario context
to reduce repetition across generated scenarios.
"""
import random
from typing import Optional

# ── Surname pool (22) ─────────────────────────────────────────────────────────
SURNAMES = [
    "王", "李", "張", "劉", "陳", "楊", "黃", "趙", "吳", "周",
    "林", "蔡", "梁", "何", "鄭", "謝", "羅", "徐", "孫", "朱",
    "胡", "郭"
]

# ── Given names ───────────────────────────────────────────────────────────────
MALE_CHINESE = [
    "偉", "強", "勇", "軍", "傑",                          # China top 5
    "家豪", "志明", "建宏", "俊傑", "文雄",                 # Taiwan top 5
    "宇軒", "子謙", "家樂",                                  # Hong Kong top 3
]

FEMALE_CHINESE = [
    "芳", "英", "娜", "靜", "麗",                           # China top 5
    "淑芬", "淑惠", "美玲", "雅婷", "麗華",                 # Taiwan top 5
    "曉晴", "凱琳", "嘉怡",                                  # Hong Kong top 3
]

MALE_ENGLISH = [
    "David", "Kevin", "Jason", "Brian", "Michael",
    "Eric", "Daniel", "Andrew", "Jonathan", "Timothy"
]

FEMALE_ENGLISH = [
    "Amy", "Jennifer", "Grace", "Vivian", "Christine",
    "Angela", "Cindy", "Michelle", "Rachel", "Stephanie"
]

# ── Title pools ───────────────────────────────────────────────────────────────
TITLES_CHURCH = ["長老", "執事", "牧師", "師母", "組長"]
TITLES_FAMILY_AGE = ["伯伯", "阿姨", "大哥", "大姐"]
TITLES_GENERIC = ["弟兄", "姊妹"]

# ── English-appropriate contexts ──────────────────────────────────────────────
ENGLISH_NAME_CONTEXTS = {"灣區教會", "北美華人教會", "香港教會"}


def generate_name(
    gender: str = "male",
    setting: str = "灣區教會",
    used_names: Optional[set] = None,
    relationship_context: str = "",
) -> str:
    """
    Generate a name for a scenario protagonist.

    Rules:
    - English-appropriate settings: 67% Chinese, 33% English
    - Asian settings: 100% Chinese
    - 75% full name, 25% title
    - English names: first name only (no surname)
    - Chinese title format: surname + title (陳長老) or generic title alone (弟兄)
    - Tracks used_names to avoid repetition within a session

    Args:
        gender: "male" or "female"
        setting: scenario context setting
        used_names: set of names already used in this session
        relationship_context: hints for title selection (church/family/workplace)

    Returns:
        A name string ready to insert into the scenario prompt
    """
    if used_names is None:
        used_names = set()

    use_english = (
        setting in ENGLISH_NAME_CONTEXTS and random.random() < 0.33
    )
    use_title = random.random() < 0.25

    if use_title:
        surname = random.choice([s for s in SURNAMES if s not in used_names] or SURNAMES)
        # Choose title pool based on context hints
        if "church" in relationship_context.lower() or any(
            t in relationship_context for t in ["小組", "教會", "事工", "長老", "執事"]
        ):
            title = random.choice(TITLES_CHURCH)
            name = f"{surname}{title}"
        elif any(t in relationship_context for t in ["家庭", "夫妻", "長輩"]):
            title = random.choice(TITLES_FAMILY_AGE)
            name = f"{surname}{title}"
        else:
            # Generic — title alone
            name = random.choice(TITLES_GENERIC)
        used_names.add(name)
        return name

    if use_english:
        pool = MALE_ENGLISH if gender == "male" else FEMALE_ENGLISH
        available = [n for n in pool if n not in used_names]
        if not available:
            available = pool
        name = random.choice(available)
        used_names.add(name)
        return name

    # Chinese full name
    given_pool = MALE_CHINESE if gender == "male" else FEMALE_CHINESE
    available_given = [n for n in given_pool if n not in used_names]
    if not available_given:
        available_given = given_pool
    available_surnames = [s for s in SURNAMES if s not in used_names]
    if not available_surnames:
        available_surnames = SURNAMES

    surname = random.choice(available_surnames)
    given = random.choice(available_given)
    name = f"{surname}{given}"
    used_names.add(name)
    return name


def build_context_paragraph(context: dict) -> str:
    """
    Build a context paragraph to prepend to the scenario prompt.
    Only includes dimensions that were explicitly set (non-default).

    Args:
        context: dict with keys setting, profession, life_stage,
                 relationship_context, protagonist_name, protagonist_gender

    Returns:
        A short paragraph string for the prompt, or empty string if all defaults
    """
    parts = []

    setting = context.get("setting", "灣區教會")
    profession = context.get("profession", "")
    life_stage = context.get("life_stage", "")
    relationship = context.get("relationship_context", "")
    name = context.get("protagonist_name", "")
    gender = context.get("protagonist_gender", "male")

    if name:
        pronoun = "他" if gender == "male" else "她"
        parts.append(f"情境主角的名字是{name}（{pronoun}）。")

    if setting:
        parts.append(f"情境背景設定在{setting}。")

    if profession:
        parts.append(f"主角的職業或角色是{profession}。")

    if life_stage:
        parts.append(f"主角目前的人生階段：{life_stage}。")

    if relationship:
        parts.append(f"情境中的主要關係是{relationship}。")

    if not parts:
        return ""

    return (
        "SCENARIO CONTEXT (use these details to ground the scenario):\n"
        + " ".join(parts)
        + "\n\nDo not introduce other characters with the same name as the protagonist. "
        + "Use the name exactly as given throughout the scenario.\n\n"
    )
