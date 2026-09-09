"""
nlu.py
------
עטיפה סביב Gemini API. שני תפקידים בלבד, כמו שההנחיות מבקשות:

1. extract_intent(text)  -> שכבה 1 (NLU): טקסט חופשי -> JSON מובנה.
   פרומפט קשיח שמכריח JSON בלבד, כדי שאפשר יהיה לפרסר בקוד בביטחון.

2. phrase_reply(facts)   -> שכבה 4: מנסח תשובה טבעית על בסיס עובדות
   *אמיתיות* שכבר הובאו מה-DB (לא נותנים ל-Gemini "להמציא" תאריכים -
   רק לנסח בעברית טבעית את מה שכבר וידאנו).

שתי הפונקציות עובדות עם נפילה חינה (graceful fallback) לתבנית קבועה
אם אין מפתח API / אין רשת - כדי שהשרת לא יקרוס בסביבת פיתוח/בדיקה.
"""

import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')
GEMINI_URL = (
    f'https://generativelanguage.googleapis.com/v1beta/models/'
    f'{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}'
)

EXTRACTION_SYSTEM_PROMPT = """
את/ה שכבת חילוץ מידע (NLU) עבור צ'אטבוט של מספרה.
קיבלת משפט חופשי בעברית מלקוח. עליך להחזיר אך ורק אובייקט JSON תקין,
בלי טקסט נוסף, בלי הסברים, בלי markdown fences, במבנה הבא בדיוק:

{
  "name": "<שם פרטי או מלא שהוזכר, או null אם אין>",
  "claimed_date": "<תאריך בפורמט YYYY-MM-DD אם הוזכר, אחרת null>",
  "teudat_zehut": "<מספר תעודת זהות אם הוזכר, אחרת null>",
  "confirmation": "<'yes' אם המשתמש מאשר/מסכים, 'no' אם מכחיש/מסרב, אחרת null>"
}

החזר/י JSON בלבד.
"""


def _call_gemini(system_prompt, user_text):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {"temperature": 0.2}
    }
    resp = requests.post(GEMINI_URL, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _fallback_extract(text):
    """
    Fallback דטרמיניסטי (regex) — משמש כשאין מפתח Gemini/רשת, כדי
    שאפשר יהיה להריץ ולבדוק את הלוגיקה בלי תלות ברשת חיצונית.
    לא תחליף אמיתי ל-NLU, רק רשת ביטחון לפיתוח/הדגמה.
    """
    result = {"name": None, "claimed_date": None, "teudat_zehut": None, "confirmation": None}

    id_match = re.search(r'\b\d{9}\b', text)
    if id_match:
        result["teudat_zehut"] = id_match.group(0)

    date_match = re.search(r'(\d{1,2})[./](\d{1,2})[./](\d{4})', text)
    if date_match:
        d, m, y = date_match.groups()
        result["claimed_date"] = f"{y}-{int(m):02d}-{int(d):02d}"
    else:
        iso_match = re.search(r'\d{4}-\d{2}-\d{2}', text)
        if iso_match:
            result["claimed_date"] = iso_match.group(0)

    if any(w in text for w in ["כן", "נכון", "אישור"]):
        result["confirmation"] = "yes"
    elif any(w in text for w in ["לא נכון", "לא זה", "טעות"]) or text.strip() == "לא":
        result["confirmation"] = "no"

    prefix_match = re.search(r'קוראים לי\s+(.+)', text)
    if prefix_match:
        stopwords = {"ויש", "יש", "עם", "בתאריך", "תור", "ב", "לי", "ה"}
        name_words = []
        for w in prefix_match.group(1).split():
            w_clean = w.strip(",.")
            if w_clean in stopwords or re.search(r'\d', w_clean):
                break
            name_words.append(w_clean)
            if len(name_words) >= 2:
                break
        if name_words:
            result["name"] = " ".join(name_words)
    elif result["teudat_zehut"] is None and result["claimed_date"] is None and result["confirmation"] is None:
        # הודעה קצרה בלי סימנים אחרים -> כנראה שם (למשל תשובה להבהרה)
        cleaned = text.strip()
        if 0 < len(cleaned) <= 30:
            result["name"] = cleaned

    return result


def extract_intent(text):
    try:
        raw = _call_gemini(EXTRACTION_SYSTEM_PROMPT, text)
        cleaned = raw.strip().strip('`')
        if cleaned.startswith('json'):
            cleaned = cleaned[4:].strip()
        return json.loads(cleaned)
    except Exception:
        return _fallback_extract(text)


def phrase_reply(facts_summary):
    """
    facts_summary: מחרוזת שמתארת בעברית את העובדות המאומתות (לא JSON חופשי -
    רק טקסט שאנחנו כבר בנינו מה-DB, כדי ש-Gemini רק "ינסח מחדש" ולא ימציא).
    """
    system_prompt = (
        "את/ה עוזר/ת וירטואלי/ת אדיב/ה של מספרה. קיבלת רשימת עובדות מאומתות "
        "שכבר נבדקו מול המערכת. נסח/י מהן תשובה טבעית, קצרה ואדיבה בעברית, "
        "בלי להוסיף שום פרט שלא הופיע ברשימה, ובלי להמציא נתונים."
    )
    try:
        return _call_gemini(system_prompt, facts_summary).strip()
    except Exception:
        return facts_summary  # fallback: הצגת העובדות כמו שהן
