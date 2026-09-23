import re
from typing import Dict, Any, List, Tuple

# Construction and Real Estate Domain Dictionaries
HIGH_RISK_KEYWORDS = [
    "부실시공", "철근누락", "순살", "붕괴", "지반침하", "균열", "크랙",
    "누수", "침수", "중대재해", "사망", "추락사", "압수수색", "영업정지",
    "고발", "고소", "소송", "비대위", "분쟁", "입주지연", "공사중단",
    "유치권", "계약해지", "입주거부", "시위", "집단행동", "안전진단 불합격"
]

MEDIUM_RISK_KEYWORDS = [
    "하자", "마감불량", "결로", "곰팡이", "악취", "배관막힘", "도색불량",
    "단차", "타일들뜸", "미분양", "분양가논란", "공사소음", "분진", "민원",
    "설계변경", "옵션장사", "공사지연", "불만", "분통", "항의", "피해",
    "우려", "논란", "비판", "잡음"
]

POSITIVE_KEYWORDS = [
    "랜드마크", "대장아파트", "대장주", "프리미엄", "명품주거", "입주축하",
    "완판", "청약대박", "경쟁률치열", "우수시공", "친환경", "수주성공",
    "수주체결", "신고가", "호재", "역세권", "살기좋은", "탄탄한",
    "품질만족", "호평", "칭찬", "기대감", "상승세", "선호도"
]

def is_noise(text: str, negative_keywords: List[str]) -> bool:
    """Check if the post is unrelated noise (e.g. restaurants, menus, pensions)."""
    text_lower = text.lower()
    for nkw in negative_keywords:
        if nkw.lower() in text_lower:
            # Check if there is clear apartment/construction context despite the word
            real_estate_terms = ["아파트", "분양", "단지", "세대", "시공", "건설", "청약", "입주", "재개발"]
            if not any(term in text_lower for term in real_estate_terms):
                return True
    return False

def analyze_text(
    title: str,
    snippet: str = "",
    negative_keywords: List[str] = None
) -> Dict[str, Any]:
    """
    Analyzes post content for sentiment, construction risk level, and score.
    Returns:
        dict: {
            'is_noise': bool,
            'sentiment': 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL',
            'risk_level': 'HIGH' | 'MEDIUM' | 'INFO' | 'SAFE',
            'risk_score': int (0-100),
            'detected_risks': List[str],
            'detected_positives': List[str]
        }
    """
    full_text = f"{title} {snippet}".strip()
    
    # 1. Noise check
    if negative_keywords and is_noise(full_text, negative_keywords):
        return {
            "is_noise": True,
            "sentiment": "NEUTRAL",
            "risk_level": "SAFE",
            "risk_score": 0,
            "detected_risks": [],
            "detected_positives": []
        }
        
    detected_high = [kw for kw in HIGH_RISK_KEYWORDS if kw in full_text]
    detected_medium = [kw for kw in MEDIUM_RISK_KEYWORDS if kw in full_text]
    detected_positive = [kw for kw in POSITIVE_KEYWORDS if kw in full_text]
    
    all_risks = detected_high + detected_medium
    
    # 2. Risk scoring & level calculation
    risk_score = 0
    if detected_high:
        # Base 80 for high risk + 5 per additional word, up to 100
        risk_score = min(100, 80 + (len(detected_high) - 1) * 7 + len(detected_medium) * 3)
        risk_level = "HIGH"
        sentiment = "NEGATIVE"
    elif detected_medium:
        # Base 50 for medium risk + 6 per additional word, up to 79
        risk_score = min(79, 50 + (len(detected_medium) - 1) * 6)
        risk_level = "MEDIUM"
        sentiment = "NEGATIVE"
    elif detected_positive:
        risk_score = max(5, 30 - len(detected_positive) * 5)
        risk_level = "INFO"
        sentiment = "POSITIVE"
    else:
        risk_score = 0
        risk_level = "SAFE"
        sentiment = "NEUTRAL"
        
    return {
        "is_noise": False,
        "sentiment": sentiment,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "detected_risks": all_risks,
        "detected_positives": detected_positive
    }
