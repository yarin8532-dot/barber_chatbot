"""
conversation.py
----------------
ניהול מצב שיחה - "הבוט צריך לזכור בין הודעה להודעה מי זה המועמד הנוכחי
ואם הוא כבר אומת" (דרישה מפורשת בהנחיות).

מימוש in-memory לפי session_id. מספיק לפרויקט לימודי (Flask dev server,
תהליך יחיד). בפרודקשן אמיתי היה צריך Redis/DB, אבל זה מעבר להיקף הקורס.
"""

MAX_ID_ATTEMPTS = 3

_SESSIONS = {}


def get_session(session_id):
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = {
            "stage": "start",          # start | await_clarification | await_name_confirmation | await_id | verified | blocked
            "candidate_id": None,
            "candidate_name": None,
            "claimed_date": None,
            "id_attempts": 0,
            "token": None,
        }
    return _SESSIONS[session_id]


def reset_session(session_id):
    _SESSIONS[session_id] = {
        "stage": "start",
        "candidate_id": None,
        "candidate_name": None,
        "claimed_date": None,
        "id_attempts": 0,
        "token": None,
    }
    return _SESSIONS[session_id]
