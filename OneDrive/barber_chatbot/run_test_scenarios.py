import os
if os.path.exists('barber_shop.db'):
    os.remove('barber_shop.db')

import db_manager
db_manager.init_db()
db_manager.seed_data()

from app import app

client = app.test_client()

def send(session_id, msg):
    r = client.post('/chat', json={"session_id": session_id, "message": msg})
    reply = r.get_json()['reply']
    print(f"  משתמש: {msg}")
    print(f"  בוט:    {reply}")
    print()
    return reply

def scenario(title, session_id, turns):
    print("=" * 70)
    print(title)
    print("=" * 70)
    for t in turns:
        send(session_id, t)
    print()


scenario(
    "תרחיש 1: שם ייחודי + תאריך שגוי שהמשתמש טוען -> תיקון",
    "s1",
    [
        "קוראים לי רותם מירון ויש לי תור בתאריך 18.01.2027",
        "כן",
        "123456789",
    ]
)

scenario(
    "תרחיש 2: שם לא ייחודי (2 לקוחות בשם רותם) -> הבהרה",
    "s2",
    [
        "קוראים לי רותם",
        "רותם כהן",
        "987654321",
    ]
)

scenario(
    "תרחיש 3: תעודת זהות שגויה -> סירוב מנומס, בלי לחשוף פרטים",
    "s3",
    [
        "קוראים לי דנה לוי",
        "כן",
        "000000000",
        "111111111",
        "222222222",  # ניסיון שלישי כושל -> חסימה
        "אפשר בכל זאת לדעת מתי התור שלי?",  # אחרי חסימה
    ]
)

scenario(
    "תרחיש 4: לקוח קיים בלי אף תור פתוח",
    "s4",
    [
        "קוראים לי יוסי אברהם",
        "כן",
        "222333444",
    ]
)

scenario(
    "תרחיש 5: שם שלא קיים בכלל במערכת",
    "s5",
    [
        "קוראים לי אבישג פלונית",
    ]
)
