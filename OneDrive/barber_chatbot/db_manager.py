"""
db_manager.py
-------------
שכבת גישה לבסיס הנתונים של Yarin Barber Shop.

שינוי מהותי לעומת פרויקט האמצע:
במקום client_name כטקסט חופשי בתוך appointments, יש עכשיו Entity נפרד
של 'customers' עם תעודת זהות (teudat_zehut) — כי כל תהליך האימות
בפרויקט הגמר חייב להשוות ת"ז אמיתית מול משהו ששמור במערכת.
appointments מקושר אל customers דרך customer_id (foreign key).
"""

import sqlite3

DB_NAME = 'barber_shop.db'


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            teudat_zehut TEXT NOT NULL UNIQUE,
            phone TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            service_type TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    ''')

    conn.commit()
    conn.close()


def seed_data(force=False):
    """
    מזין נתוני דוגמה אמיתיים (לפחות 5 שורות לכל Entity, כנדרש בהנחיות).
    כולל בכוונה:
      - שני לקוחות עם אותו שם פרטי ('רותם') -> לבדיקת שם לא ייחודי.
      - לקוח אחד בלי אף תור -> לבדיקת "לקוח בלי תור".
      - לקוח 'רותם מירון' עם תור אמיתי ב-19.01.2027, בדיוק כמו בדוגמת
        השיחה בהנחיות (שם המשתמש טעה וחשב שזה 18.01).
    """
    conn = get_conn()
    cursor = conn.cursor()

    if not force:
        cursor.execute('SELECT COUNT(*) FROM customers')
        if cursor.fetchone()[0] > 0:
            conn.close()
            return  # כבר יש נתונים, לא דורסים

    customers = [
        ('רותם מירון',     '123456789', '050-1111111'),
        ('רותם כהן',      '987654321', '050-2222222'),
        ('דנה לוי',        '111222333', '050-3333333'),
        ('יוסי אברהם',     '222333444', '050-4444444'),  # בלי תורים בכוונה
        ('שירה בן דוד',    '333444555', '050-5555555'),
    ]
    cursor.executemany(
        'INSERT INTO customers (full_name, teudat_zehut, phone) VALUES (?, ?, ?)',
        customers
    )

    # ממפים שם -> id כדי לבנות תורים
    cursor.execute('SELECT id, full_name FROM customers')
    ids = {row['full_name']: row['id'] for row in cursor.fetchall()}

    appointments = [
        (ids['רותם מירון'],  'תספורת',        '2027-01-19', '19:00', 'ממתין'),
        (ids['רותם כהן'],    'תספורת+זקן',    '2027-01-20', '10:00', 'ממתין'),
        (ids['דנה לוי'],     'תספורת',        '2027-01-21', '11:00', 'בוצע'),
        (ids['שירה בן דוד'], 'זקן',           '2027-01-22', '15:30', 'ממתין'),
        (ids['דנה לוי'],     'זקן',           '2027-01-25', '09:00', 'בוטל'),
    ]
    cursor.executemany('''
        INSERT INTO appointments (customer_id, service_type, appointment_date, appointment_time, status)
        VALUES (?, ?, ?, ?, ?)
    ''', appointments)

    conn.commit()
    conn.close()


# ---------- לקוחות ----------

def find_customers_by_name(partial_name):
    """חיפוש לקוחות לפי שם חלקי (לא חושף ת"ז!)."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, full_name FROM customers
        WHERE full_name LIKE ?
        ORDER BY full_name
    ''', (f'%{partial_name}%',))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_customer(customer_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT id, full_name FROM customers WHERE id = ?', (customer_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def verify_customer_id(customer_id, teudat_zehut):
    """משווה ת"ז מוצהרת מול הת"ז השמורה עבור אותו customer_id בלבד."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT teudat_zehut FROM customers WHERE id = ?', (customer_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return False
    return row['teudat_zehut'] == str(teudat_zehut).strip()


# ---------- תורים ----------

def get_appointments_by_customer(customer_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, service_type, appointment_date, appointment_time, status
        FROM appointments
        WHERE customer_id = ?
        ORDER BY appointment_date, appointment_time
    ''', (customer_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def add_appointment(customer_id, service, date, time):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM appointments
        WHERE appointment_date = ? AND appointment_time = ? AND status != 'בוטל'
    ''', (date, time))
    if len(cursor.fetchall()) > 0:
        conn.close()
        return False, "התאריך והשעה הזו כבר תפוסים!"
    cursor.execute('''
        INSERT INTO appointments (customer_id, service_type, appointment_date, appointment_time, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (customer_id, service, date, time, "ממתין"))
    conn.commit()
    conn.close()
    return True, "התור נוסף בהצלחה!"


def update_appointment_status(appointment_id, customer_id, new_status):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE appointments SET status = ?
        WHERE id = ? AND customer_id = ?
    ''', (new_status, appointment_id, customer_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_appointment(appointment_id, customer_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM appointments WHERE id = ? AND customer_id = ?', (appointment_id, customer_id))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def view_all_appointments():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.id, c.full_name, a.service_type, a.appointment_date, a.appointment_time, a.status
        FROM appointments a JOIN customers c ON a.customer_id = c.id
        ORDER BY a.appointment_date, a.appointment_time
    ''')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
