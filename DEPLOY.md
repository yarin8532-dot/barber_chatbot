# DEPLOY.md — Yarin Barber Shop Chatbot

## הרצה מקומית (Local)

1. שכפול הריפו:
   ```bash
   git clone <REPO_URL>
   cd barber_chatbot
   ```
2. סביבה וירטואלית (מומלץ) + התקנת תלויות:
   ```bash
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. הגדרת מפתח Gemini:
   ```bash
   cp .env.example .env
   # ערכו את .env והכניסו GEMINI_API_KEY אמיתי
   export $(cat .env | xargs)      # או שימוש ב-python-dotenv אם מוסיפים אותו
   ```
4. הרצה:
   ```bash
   python app.py
   ```
   האפליקציה תעלה על `http://localhost:5000`. בהרצה הראשונה `init_db()` +
   `seed_data()` יוצרים את `barber_shop.db` עם נתוני דוגמה (5 לקוחות, 5 תורים).

   > אם אין `GEMINI_API_KEY` מוגדר, המערכת עדיין עובדת — שכבת ה-NLU נופלת
   > אוטומטית ל-fallback דטרמיניסטי (regex) כדי שאפשר יהיה לבדוק את
   > הלוגיקה גם בלי רשת/מפתח. לחוויית שיחה טבעית אמיתית צריך מפתח Gemini.

## עדכון שרת (נוהל DevOps ידני, קבוע וחוזר)

אין CI/CD אוטומטי בפרויקט הזה — אבל **יש נוהל אחיד וקבוע** לכל עדכון:

1. מתחברים לשרת (SSH):
   ```bash
   ssh <user>@<server-ip>
   ```
2. עוברים לתיקיית הפרויקט ומושכים את הגרסה האחרונה:
   ```bash
   cd /path/to/barber_chatbot
   git pull origin main
   ```
3. אם יש שינוי בתלויות — מעדכנים:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. מפעילים מחדש את התהליך. תלוי איך הוא רץ:
   - אם רץ תחת `screen`/`tmux`: הורגים את התהליך הישן (`Ctrl+C` / `kill <pid>`)
     ומריצים שוב `python app.py` (או `gunicorn app:app` בפרודקשן).
   - אם רץ כ-`systemd` service:
     ```bash
     sudo systemctl restart barber-chatbot.service
     ```
5. בדיקת שפיות מהירה אחרי כל דיפלוי:
   ```bash
   curl -X POST http://localhost:5000/chat \
     -H "Content-Type: application/json" \
     -d '{"session_id":"smoke","message":"קוראים לי דנה לוי"}'
   ```
   ואמור לחזור `{"reply": "קוראים לך דנה לוי?"}`.

**הערה:** זה בכוונה נוהל ידני מתועד (git pull + restart), לא pipeline
אוטומטי — כפי שהוגדר בהנחיות ("DevOps מינימלי, לא CI/CD מלא").
