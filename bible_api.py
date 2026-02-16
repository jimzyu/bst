"""
Bible API client for fetching Bible passages.
Uses api.bible for ESV (English) and CUV (Chinese Union Version).
"""
import logging
import requests
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class BibleAPIClient:
    """Client for fetching Bible passages from api.bible."""
    
    # API endpoints
    BASE_URL = "https://rest.api.bible/v1"
    
    # Bible IDs (from api.bible)
    BIBLE_NIRV = "5b888a42e2d9a89d-01"  # New International Reader's Version (NIrV)
    BIBLE_FEB = "04fb2bec0d582d1f-01"   # Chinese Free Easy-to-Read Bible (FEB)
    
    def __init__(self, api_key: str):
        """
        Initialize Bible API client.
        
        Args:
            api_key: API key from api.bible (free tier: 500 requests/day)
        """
        self.api_key = api_key
        self.headers = {
            "api-key": api_key
        }
    
    def _normalize_reference(self, reference: str) -> str:
        """
        Normalize Bible reference to api.bible format.
        
        Examples:
            "Matthew 5:1-12" -> "MAT.5.1-MAT.5.12"
            "John 3:16" -> "JHN.3.16"
            "創世記 1:1" -> "GEN.1.1" (handles Chinese book names)
        
        Args:
            reference: User-provided Bible reference
            
        Returns:
            Normalized reference string for API
        """
        # Map of book names to USFM abbreviations
        book_mapping = {
            # English names
            "genesis": "GEN", "gen": "GEN",
            "exodus": "EXO", "exo": "EXO", "ex": "EXO",
            "leviticus": "LEV", "lev": "LEV",
            "numbers": "NUM", "num": "NUM",
            "deuteronomy": "DEU", "deut": "DEU",
            "joshua": "JOS", "josh": "JOS",
            "judges": "JDG", "judg": "JDG",
            "ruth": "RUT",
            "1 samuel": "1SA", "1sa": "1SA", "1sam": "1SA",
            "2 samuel": "2SA", "2sa": "2SA", "2sam": "2SA",
            "1 kings": "1KI", "1ki": "1KI",
            "2 kings": "2KI", "2ki": "2KI",
            "1 chronicles": "1CH", "1ch": "1CH",
            "2 chronicles": "2CH", "2ch": "2CH",
            "ezra": "EZR",
            "nehemiah": "NEH", "neh": "NEH",
            "esther": "EST",
            "job": "JOB",
            "psalm": "PSA", "psalms": "PSA", "ps": "PSA",
            "proverbs": "PRO", "prov": "PRO",
            "ecclesiastes": "ECC", "eccl": "ECC",
            "song of solomon": "SNG", "song": "SNG",
            "isaiah": "ISA", "isa": "ISA",
            "jeremiah": "JER", "jer": "JER",
            "lamentations": "LAM", "lam": "LAM",
            "ezekiel": "EZK", "ezek": "EZK",
            "daniel": "DAN", "dan": "DAN",
            "hosea": "HOS", "hos": "HOS",
            "joel": "JOL",
            "amos": "AMO",
            "obadiah": "OBA", "obad": "OBA",
            "jonah": "JON",
            "micah": "MIC", "mic": "MIC",
            "nahum": "NAM", "nah": "NAM",
            "habakkuk": "HAB", "hab": "HAB",
            "zephaniah": "ZEP", "zeph": "ZEP",
            "haggai": "HAG", "hag": "HAG",
            "zechariah": "ZEC", "zech": "ZEC",
            "malachi": "MAL", "mal": "MAL",
            "matthew": "MAT", "matt": "MAT", "mt": "MAT",
            "mark": "MRK", "mk": "MRK",
            "luke": "LUK", "lk": "LUK",
            "john": "JHN", "jn": "JHN",
            "acts": "ACT",
            "romans": "ROM", "rom": "ROM",
            "1 corinthians": "1CO", "1co": "1CO", "1cor": "1CO",
            "2 corinthians": "2CO", "2co": "2CO", "2cor": "2CO",
            "galatians": "GAL", "gal": "GAL",
            "ephesians": "EPH", "eph": "EPH",
            "philippians": "PHP", "phil": "PHP",
            "colossians": "COL", "col": "COL",
            "1 thessalonians": "1TH", "1th": "1TH", "1thess": "1TH",
            "2 thessalonians": "2TH", "2th": "2TH", "2thess": "2TH",
            "1 timothy": "1TI", "1ti": "1TI", "1tim": "1TI",
            "2 timothy": "2TI", "2ti": "2TI", "2tim": "2TI",
            "titus": "TIT", "tit": "TIT",
            "philemon": "PHM", "phlm": "PHM",
            "hebrews": "HEB", "heb": "HEB",
            "james": "JAS", "jas": "JAS",
            "1 peter": "1PE", "1pe": "1PE", "1pet": "1PE",
            "2 peter": "2PE", "2pe": "2PE", "2pet": "2PE",
            "1 john": "1JN", "1jn": "1JN",
            "2 john": "2JN", "2jn": "2JN",
            "3 john": "3JN", "3jn": "3JN",
            "jude": "JUD",
            "revelation": "REV", "rev": "REV",
            
            # Chinese names (Traditional)
            "創世記": "GEN", "出埃及記": "EXO", "利未記": "LEV", "民數記": "NUM",
            "申命記": "DEU", "約書亞記": "JOS", "士師記": "JDG", "路得記": "RUT",
            "撒母耳記上": "1SA", "撒母耳記下": "2SA", "列王紀上": "1KI", "列王紀下": "2KI",
            "歷代志上": "1CH", "歷代志下": "2CH", "以斯拉記": "EZR", "尼希米記": "NEH",
            "以斯帖記": "EST", "約伯記": "JOB", "詩篇": "PSA", "箴言": "PRO",
            "傳道書": "ECC", "雅歌": "SNG", "以賽亞書": "ISA", "耶利米書": "JER",
            "耶利米哀歌": "LAM", "以西結書": "EZK", "但以理書": "DAN", "何西阿書": "HOS",
            "約珥書": "JOL", "阿摩司書": "AMO", "俄巴底亞書": "OBA", "約拿書": "JON",
            "彌迦書": "MIC", "那鴻書": "NAM", "哈巴谷書": "HAB", "西番雅書": "ZEP",
            "哈該書": "HAG", "撒迦利亞書": "ZEC", "瑪拉基書": "MAL",
            "馬太福音": "MAT", "馬可福音": "MRK", "路加福音": "LUK", "約翰福音": "JHN",
            "使徒行傳": "ACT", "羅馬書": "ROM", "哥林多前書": "1CO", "哥林多後書": "2CO",
            "加拉太書": "GAL", "以弗所書": "EPH", "腓立比書": "PHP", "歌羅西書": "COL",
            "帖撒羅尼迦前書": "1TH", "帖撒羅尼迦後書": "2TH", "提摩太前書": "1TI",
            "提摩太後書": "2TI", "提多書": "TIT", "腓利門書": "PHM", "希伯來書": "HEB",
            "雅各書": "JAS", "彼得前書": "1PE", "彼得後書": "2PE", "約翰一書": "1JN",
            "約翰二書": "2JN", "約翰三書": "3JN", "猶大書": "JUD", "啟示錄": "REV"
        }
        
        # Extract book name and chapter:verse pattern
        # Pattern: "Book Chapter:Verse" or "Book Chapter:Verse-Verse"
        pattern = r'(.+?)\s+(\d+):(\d+)(?:-(\d+))?'
        match = re.match(pattern, reference.strip())
        
        if not match:
            # If no match, return as-is and let API handle it
            return reference
        
        book_name = match.group(1).strip().lower()
        chapter = match.group(2)
        start_verse = match.group(3)
        end_verse = match.group(4)
        
        # Get book abbreviation
        book_abbr = book_mapping.get(book_name)
        if not book_abbr:
            # Try without spaces for compound names
            book_name_no_space = book_name.replace(" ", "")
            book_abbr = book_mapping.get(book_name_no_space, book_name.upper()[:3])
        
        # Build normalized reference
        if end_verse:
            # Range: MAT.5.1-MAT.5.12
            normalized = f"{book_abbr}.{chapter}.{start_verse}-{book_abbr}.{chapter}.{end_verse}"
        else:
            # Single verse: MAT.5.1
            normalized = f"{book_abbr}.{chapter}.{start_verse}"
        
        return normalized
    
    def fetch_passage(self, reference: str, language: str = "english") -> Optional[Tuple[str, str]]:
        """
        Fetch Bible passage text.
        
        Args:
            reference: Bible reference (e.g., "Matthew 5:1-12")
            language: "english" or "chinese"
            
        Returns:
            Tuple of (formatted_reference, passage_text) or None if failed
        """
        bible_id = self.BIBLE_NIRV if language == "english" else self.BIBLE_FEB
        
        try:
            # Normalize reference
            normalized_ref = self._normalize_reference(reference)
            logger.info(f"Fetching passage: {reference} -> {normalized_ref} ({language})")
            
            # Build API request
            url = f"{self.BASE_URL}/bibles/{bible_id}/passages/{normalized_ref}"
            params = {
                "content-type": "text",
                "include-notes": "false",
                "include-titles": "true",
                "include-chapter-numbers": "false",
                "include-verse-numbers": "true",
                "include-verse-spans": "false"
            }
            
            logger.info(f"API URL: {url}")
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            # Log response status
            logger.info(f"API Response Status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"API Error Response: {response.text}")
            
            response.raise_for_status()
            
            data = response.json()
            
            # Extract passage data
            passage_data = data.get("data", {})
            passage_text = passage_data.get("content", "")
            formatted_ref = passage_data.get("reference", reference)
            
            if passage_text:
                logger.info(f"Successfully fetched passage: {formatted_ref} ({len(passage_text)} chars)")
                return formatted_ref, passage_text
            else:
                logger.warning(f"Empty passage returned for: {reference}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {reference}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error fetching passage {reference}: {str(e)}")
            return None
    
    def fetch_both_languages(self, reference: str) -> Optional[dict]:
        """
        Fetch passage in both English and Chinese.
        
        Args:
            reference: Bible reference
            
        Returns:
            Dict with keys 'english' and 'chinese', each containing (reference, text) tuples
            or None if both failed
        """
        result = {}
        
        # Fetch English
        english_data = self.fetch_passage(reference, "english")
        if english_data:
            result['english'] = english_data
        
        # Fetch Chinese
        chinese_data = self.fetch_passage(reference, "chinese")
        if chinese_data:
            result['chinese'] = chinese_data
        
        if not result:
            logger.warning(f"Failed to fetch passage in any language: {reference}")
            return None
        
        return result
