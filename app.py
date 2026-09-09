"""
app.py
------
אפליקציית ה-web (Flask). מריצה:
  - ממשק צ'אט פשוט ב-'/'
  - שכבת ה-API האמיתית תחת '/api/...' (api.py)
  - את ה-orchestration של השיחה ב-'/chat' (שכבות 1+2+3+4 מההנחיות)

חשוב: '/chat' לא נוגע ב-DB ישירות. הוא קורא לשכבת ה-API דרך
Flask test_client (קריאה פנימית אמיתית ל-HTTP endpoints), בדיוק כמו
שהיה קורה אם ה-API היה רץ על שרת נפרד. זה מדגים "שכבת שיחה מעל API קיים"
כפי שההנחיות דורשות, בלי צורך בשני תהליכים נפרדים.
"""

import os
import json
from flask import Flask, request, jsonify, render_template, session as flask_session
import uuid

import db_manager
from api import api_bp
import nlu
import conversation

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')
app.register_blueprint(api_bp)

_client = app.test_client()


# ---------- עזרי קריאה לשכבת ה-API ----------

def api_search(name):
    resp = _client.get(f'/api/customers/search?name={name}')
    return resp.get_json().get('matches', [])


def api_verify(customer_id, teudat_zehut):
    resp = _client.post('/api/customers/verify', json={
        "customer_id": customer_id, "teudat_zehut": teudat_zehut
    })
    return resp.get_json()


def api_appointments(customer_id, token):
    resp = _client.get(f'/api/appointments?customer_id={customer_id}&token={token}')
    return resp.get_json().get('appointments', [])


# ---------- לוגיקת השיחה ----------

def handle_message(session_id, message):
    sess = conversation.get_session(session_id)

    if sess['stage'] == 'blocked':
        return "השיחה ננעלה בעקבות יותר מדי ניסיונות אימות כושלים. אנא פנה/י למספרה ישירות."

    intent = nlu.extract_intent(message)

    # --- שלב פתיחה: מחפשים שם ---
    if sess['stage'] == 'start':
        if intent.get('claimed_date'):
            sess['claimed_date'] = intent['claimed_date']

        name = intent.get('name')
        if not name:
            return "היי! איך קוראים לך?"

        matches = api_search(name)
        if len(matches) == 0:
            return f"לא מצאתי לקוח/ה בשם '{name}' במערכת. אפשר לבדוק את האיות?"

        if len(matches) == 1:
            sess['candidate_id'] = matches[0]['id']
            sess['candidate_name'] = matches[0]['full_name']
            sess['stage'] = 'await_name_confirmation'
            return f"קוראים לך {matches[0]['full_name']}?"

        # כמה התאמות - לא מנחשים, מבקשים הבהרה
        sess['stage'] = 'await_clarification'
        return "מצאתי כמה לקוחות בשם הזה. מטעמי פרטיות, אשמח לשם המלא כפי שמופיע במערכת."

    # --- הבהרת שם (כשהיו כמה התאמות) ---
    if sess['stage'] == 'await_clarification':
        name_query = intent.get('name') or message.strip()
        matches = api_search(name_query)
        exact = [m for m in matches if m['full_name'] == name_query.strip()]
        chosen = exact if exact else matches

        if len(chosen) == 0:
            return "עדיין לא מצאתי התאמה. אפשר לכתוב את השם המלא בדיוק כפי שמופיע?"
        if len(chosen) > 1:
            return "עדיין מצאתי כמה התאמות. מטעמי פרטיות, אשמח לשם המלא המדויק כפי שמופיע במערכת."

        sess['candidate_id'] = chosen[0]['id']
        sess['candidate_name'] = chosen[0]['full_name']
        sess['stage'] = 'await_id'
        return f"תודה! לצורך אימות, מה תעודת הזהות שלך?"

    # --- אישור שם ---
    if sess['stage'] == 'await_name_confirmation':
        confirmation = intent.get('confirmation')
        if confirmation == 'yes':
            sess['stage'] = 'await_id'
            return "מעולה. מה תעודת הזהות שלך? (לצורך אימות בלבד)"
        if confirmation == 'no':
            conversation.reset_session(session_id)
            return "סליחה על הטעות. אז מה השם שלך?"
        return "אפשר לאשר בכן/לא? קוראים לך " + str(sess['candidate_name']) + "?"

    # --- אימות תעודת זהות ---
    if sess['stage'] == 'await_id':
        teudat = intent.get('teudat_zehut')
        if not teudat:
            return "אנא שלח/י מספר תעודת זהות (9 ספרות) לצורך אימות."

        result = api_verify(sess['candidate_id'], teudat)

        if not result.get('verified'):
            sess['id_attempts'] += 1
            if sess['id_attempts'] >= conversation.MAX_ID_ATTEMPTS:
                sess['stage'] = 'blocked'
                return "מספר תעודת הזהות שגוי, וניצלת את כל הניסיונות. מטעמי אבטחה השיחה ננעלת. אנא פנה/י למספרה ישירות."
            remaining = conversation.MAX_ID_ATTEMPTS - sess['id_attempts']
            return f"מספר תעודת הזהות אינו תואם למערכת. נסה/י שוב (נותרו {remaining} ניסיונות)."

        # אומת בהצלחה
        sess['token'] = result['token']
        reply_text = _build_verified_reply(sess)
        conversation.reset_session(session_id)  # שיחה חדשה יכולה להתחיל אחרי מענה
        return reply_text

    return "משהו השתבש, אפשר להתחיל מחדש?"


def _build_verified_reply(sess):
    appts = api_appointments(sess['candidate_id'], sess['token'])
    active = [a for a in appts if a['status'] != 'בוטל']
    name = sess['candidate_name']
    claimed = sess.get('claimed_date')

    if not active:
        facts = f"אומת בהצלחה מול {name}. אין כרגע אף תור פעיל במערכת עבור לקוח/ה זה."
    elif claimed:
        matched = next((a for a in active if a['appointment_date'] == claimed), None)
        if matched:
            facts = (f"אומת בהצלחה מול {name}. התור אכן קיים בתאריך {matched['appointment_date']} "
                     f"בשעה {matched['appointment_time']}, שירות: {matched['service_type']}, "
                     f"סטטוס: {matched['status']}. אין פער בין מה שהמשתמש טען לבין המערכת.")
        else:
            real = active[0]
            facts = (f"אומת בהצלחה מול {name}. המשתמש טען שהתור בתאריך {claimed}, "
                     f"אבל בפועל התור האמיתי במערכת הוא בתאריך {real['appointment_date']} "
                     f"בשעה {real['appointment_time']}, שירות: {real['service_type']}. "
                     f"יש לציין ללקוח את הפער בעדינות ולתת את הפרטים הנכונים.")
    else:
        lines = "; ".join(
            f"{a['appointment_date']} בשעה {a['appointment_time']} ({a['service_type']}, {a['status']})"
            for a in active
        )
        facts = f"אומת בהצלחה מול {name}. התורים הפעילים שלו/ה: {lines}."

    return nlu.phrase_reply(facts)


# ---------- Routes ----------

@app.route('/')
def index():
    if 'session_id' not in flask_session:
        flask_session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True) or {}
    session_id = data.get('session_id') or flask_session.get('session_id', 'default')
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({"reply": "אפשר לכתוב הודעה?"})
    reply = handle_message(session_id, message)
    return jsonify({"reply": reply})


if __name__ == '__main__':
    db_manager.init_db()
    db_manager.seed_data()
    app.run(debug=True, host='0.0.0.0', port=5000)
