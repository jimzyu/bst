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

# ── Title pools (gender-specific where relevant) ─────────────────────────────
TITLES_CHURCH_MALE   = ["長老", "執事", "牧師", "組長"]
TITLES_CHURCH_FEMALE = ["執事", "師母", "組長"]
TITLES_FAMILY_MALE   = ["伯伯", "大哥"]
TITLES_FAMILY_FEMALE = ["阿姨", "大姐"]
TITLES_GENERIC_MALE   = ["弟兄"]
TITLES_GENERIC_FEMALE = ["姊妹"]

# ── English-appropriate contexts ──────────────────────────────────────────────
# Regions where English names are appropriate (67% Chinese, 33% English)
ENGLISH_NAME_REGIONS = {"灣區", "北美"}


def generate_name(
    gender: str = "male",
    region: str = "灣區",
    used_names: Optional[set] = None,
    scene: str = "",
) -> str:
    """
    Generate a name for a scenario protagonist.

    Rules:
    - 灣區 / 北美 regions: 67% Chinese, 33% English names
    - 亞洲 region: 100% Chinese names
    - 75% full name, 25% title
    - English names: first name only (no surname)
    - Chinese title format: surname + title (陳長老) or generic title alone (弟兄)
    - Tracks used_names to avoid repetition within a session

    Args:
        gender: "male" or "female"
        region: 灣區 / 北美 / 亞洲
        used_names: set of names already used in this session
        scene: scenario scene (教會/職場/家庭/學校/社區) — hints for title pool

    Returns:
        A name string ready to insert into the scenario prompt
    """
    if used_names is None:
        used_names = set()

    use_english = (
        region in ENGLISH_NAME_REGIONS and random.random() < 0.33
    )
    use_title = random.random() < 0.25

    if use_title:
        surname = random.choice([s for s in SURNAMES if s not in used_names] or SURNAMES)
        # Choose title pool based on context hints
        if scene == "教會":
            pool = TITLES_CHURCH_MALE if gender == "male" else TITLES_CHURCH_FEMALE
            title = random.choice(pool)
            name = f"{surname}{title}"
        elif scene == "家庭":
            pool = TITLES_FAMILY_MALE if gender == "male" else TITLES_FAMILY_FEMALE
            title = random.choice(pool)
            name = f"{surname}{title}"
        else:
            name = TITLES_GENERIC_MALE[0] if gender == "male" else TITLES_GENERIC_FEMALE[0]
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
    Uses explicit, directive language so the model treats these as hard constraints.
    Only injects non-default values to avoid over-constraining.

    Args:
        context: dict with keys region, scene, profession, life_stage,
                 protagonist_name, protagonist_gender

    Returns:
        A directive context block for the prompt, or minimal block with just the name
    """
    name = context.get("protagonist_name", "")
    gender = context.get("protagonist_gender", "male")
    pronoun = "他" if gender == "male" else "她"
    region = context.get("region", "灣區")
    scene = context.get("scene", "")
    profession = context.get("profession", "")
    life_stage = context.get("life_stage", "")

    lines = []

    # Name — always include
    if name:
        lines.append(f"主角姓名：{name}（{pronoun}）。在整個情境中，請始終使用此名字，不要更改或替換。")

    # Scene — most important for scenario texture; always include if set
    if scene:
        lines.append(f"情境場景：{scene}。請將情境設定在{scene}環境中，而非其他場合。")

    # Profession — include only if explicitly set
    if profession:
        lines.append(f"主角職業：{profession}。請確保情境符合此職業背景。")

    # Life stage — include only if explicitly set
    if life_stage:
        lines.append(f"主角人生階段：{life_stage}。")

    # Region — only include if non-default (i.e. not 灣區, which is assumed)
    if region and region != "灣區":
        lines.append(f"地區背景：{region}。")

    if not lines:
        return ""

    block = "【情境設定指示】請嚴格按照以下設定生成情境案例：\n"
    block += "\n".join(f"- {line}" for line in lines)
    block += "\n\n"
    return block
