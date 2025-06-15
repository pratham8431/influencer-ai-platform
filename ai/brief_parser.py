# ai/brief_parser.py
import re
from typing import Dict, Any

def extract_min_subs(brief: str) -> int:
    m = re.search(r'at least\s*(\d+)(?:[kK])?', brief)
    return int(m.group(1)) * 1000 if m else 0

def extract_keywords(brief: str) -> list[str]:
    # look for words around bike/riding/cycling/vlog
    kws = set(re.findall(r'\b(bike|riding|cycle|vloggers?)\b', brief, re.IGNORECASE))
    return [kw.lower() for kw in kws]

def parse_brief(brief: str) -> Dict[str, Any]:
    return {
        "min_subs": extract_min_subs(brief),
        "keywords": extract_keywords(brief),
    }
