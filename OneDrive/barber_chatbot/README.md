# Yarin Barber Shop — צ'אטבוט אימות ותורים (פרויקט גמר)

בנוי מעל פרויקט האמצע (CLI לניהול תורים למספרה). מוסיף שכבת שיחה טבעית
+ שכבת API + אימות זהות, כנדרש בהנחיות פרויקט הגמר.

## שינוי בסיסי לעומת פרויקט האמצע

פרויקט האמצע לא כלל Entity של "לקוח" (רק `client_name` כטקסט חופשי בתוך
appointments) ולא כלל REST API בכלל (רק CLI). כדי לממש את דרישות הגמר
(אימות ת"ז, "חיפוש לקוח דרך ה-API") נוספו:
- טבלת `customers` (id, full_name, teudat_zehut, phone) — Entity חדש.
- `appointments` עכשיו מקושר ל-`customers` דרך `customer_id` (FK) במקום
  שם טקסטואלי חופשי.
- שכבת REST API אמיתית (`api.py`).

## ארכיטקטורה (4 השכבות מההנחיות)

| שכבה | קובץ | תפקיד |
|---|---|---|
| 1. NLU | `nlu.py` | קורא ל-Gemini, מחזיר JSON (`name`, `claimed_date`, `teudat_zehut`, `confirmation`). פרומפט מכריח JSON בלבד. Fallback דטרמיניסטי (regex) כשאין מפתח/רשת. |
| 2. חיפוש לקוח | `api.py` → `GET /api/customers/search` | חיפוש לפי שם חלקי. מחזיר **רק** id+full_name (בלי ת"ז, בלי תורים). כמה התאמות → הבהרה, לא ניחוש. |
| 3. אימות | `api.py` → `POST /api/customers/verify` | השוואת ת"ז מדויקת. מצליח → token זמני (10 דק'), נכשל → `verified:false`. |
| 4. תשובה מבוססת דאטה | `app.py` → `GET /api/appointments` (דורש token) + `nlu.phrase_reply` | שולף תור אמיתי, משווה לתאריך שהמשתמש טען, Gemini מנסח בעברית טבעית **בלי להמציא נתונים** — רק מנסח עובדות שכבר אומתו. |

ניהול מצב שיחה (`conversation.py`): per-session — שלב נוכחי, מועמד,
כמה ניסיוני ת"ז נכשלו, טוקן אימות.

## עמידה בדרישות ההנחיות — נקודה-נקודה

- **חיפוש לפי שם חלקי + טיפול בכמה התאמות**: `find_customers_by_name` +
  לוגיקת `await_clarification` ב-`app.py`. נבדק בתרחיש 2.
- **אימות ת"ז אמיתי מול הדאטה**: `verify_customer_id` ב-`db_manager.py`,
  נחשף רק דרך `/api/customers/verify`.
- **איסור חשיפת פרטים לפני אימות**: נאכף פעמיים — גם בלוגיקת הבוט (לא
  קוראים ל-`/api/appointments` לפני `stage == verified`), וגם ב-API עצמו
  (Endpoint התורים דורש `token` תקף, בלי טוקן מחזיר 403). נבדק בתרחיש 3.
- **הגבלת ניסיונות אימות (3) + חסימה מנומסת**: `conversation.MAX_ID_ATTEMPTS`.
  נבדק בתרחיש 3.
- **מקרי קצה**: שם לא קיים (תרחיש 5), לקוח בלי תורים (תרחיש 4), ת"ז שגויה
  (תרחיש 3) — כולם ממומשים ונבדקו בפועל.
- **ניהול מצב שיחה**: `conversation.py`, session per `session_id`.
- **Web + DevOps מינימלי**: Flask + `templates/index.html` (ממשק צ'אט),
  `DEPLOY.md` עם נוהל git pull + restart מתועד.
- **כל Entity עם 5+ שורות אמיתיות**: `seed_data()` ב-`db_manager.py` —
  5 לקוחות, 5 תורים (כולל שני "רותם" וכולל לקוח בלי תורים בכוונה).

## הרצה

ראו `DEPLOY.md`. בקצרה:
```bash
pip install -r requirements.txt
cp .env.example .env   # והכניסו GEMINI_API_KEY
python app.py
```
פתחו `http://localhost:5000`.

## בדיקות

`test_scenarios.md` — תמלול אמיתי (לא מדומיין) של 5 התרחישים הנדרשים,
שהופק על ידי הרצת `run_test_scenarios.py`.

## מה עוד נשאר לכם לעשות

1. **מפתח Gemini אמיתי**: כרגע נבדק עם fallback דטרמיניסטי (אין רשת ל-
   Gemini בסביבה שבה זה נבנה). קבלו מפתח מ-Google AI Studio, שימו ב-`.env`,
   והריצו שוב את `run_test_scenarios.py` — הלוגיקה זהה, רק הניסוח יהיה
   טבעי יותר.
2. **פריסה בפועל לשרת** (VM/VPS) ותיעוד עדכני ב-DEPLOY.md אם התהליך
   שונה אצלכם (systemd vs screen וכו').
3. **הקלטת GIF/מסך** של התרחיש המרכזי (זיהוי → הבהרה → אימות → תיקון)
   מול הממשק ב-`templates/index.html`, להגשה.
4. אם רוצים, אפשר להרחיב את ה-CLI הישן (`main.py` המקורי) לעבוד מול
   הסכמה החדשה — לא חובה לפי ההנחיות, אבל שומר גיבוי לממשק המקורי.
