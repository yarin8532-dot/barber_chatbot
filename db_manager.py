import sqlite3

# שם קובץ מסד הנתונים (יווצר אוטומטית)
DB_NAME = 'barber_shop.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            service_type TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_appointment(name, service, date, time):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # בדיקה האם התאריך והשעה כבר תפוסים (לתור שלא בוטל)
    cursor.execute('''
        SELECT id FROM appointments 
        WHERE appointment_date = ? AND appointment_time = ? AND status != 'בוטל'
    ''', (date, time))
    
    if len(cursor.fetchall()) > 0:
        print("Error: This date and time are already taken! Please choose another time.")
    else:
        # ברירת המחדל לסטטוס היא 'ממתין'
        cursor.execute('''
            INSERT INTO appointments (client_name, service_type, appointment_date, appointment_time, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, service, date, time, "ממתין"))
        conn.commit()
        print("Appointment added successfully!")
        
    conn.close()

def update_status_by_name():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    search_name = input("Enter the client name to update status: ").strip()
    
    cursor.execute('''
        SELECT id, client_name, appointment_date, appointment_time, service_type, status 
        FROM appointments WHERE client_name = ?
    ''', (search_name,))
    appointments_list = cursor.fetchall()
    
    if len(appointments_list) == 0:
        print("No appointment found for this name.")
    else:
        print("\n--- Found Appointments ---")
        for app in appointments_list:
            print(f"ID: {app[0]} | Date: {app[2]} | Time: {app[3]} | Service: {app[4]} | Status: [{app[5]}]")
        print("-" * 40)
        
        app_id = input("Enter the ID of the appointment you want to update: ").strip()
        new_status = input("Enter new status (e.g., 'בוצע' / 'בוטל' / 'ממתין'): ").strip()
        
        cursor.execute('''
            UPDATE appointments
            SET status = ?
            WHERE id = ? AND client_name = ?
        ''', (new_status, app_id, search_name))
        
        if cursor.rowcount > 0:
            conn.commit()
            print("Status updated successfully!")
        else:
            print("Error: ID not found or doesn't match the client name.")
            
    conn.close()

def delete_appointment_by_name():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    search_name = input("Enter the client name to delete an appointment: ").strip()
    
    cursor.execute('''
        SELECT id, appointment_date, appointment_time, service_type, status 
        FROM appointments WHERE client_name = ?
    ''', (search_name,))
    appointments_list = cursor.fetchall()
    
    if len(appointments_list) == 0:
        print("No appointment found for this name.")
    else:
        print("\n--- Found Appointments ---")
        for app in appointments_list:
            print(f"ID: {app[0]} | Date: {app[1]} | Time: {app[2]} | Service: {app[3]} | Status: [{app[4]}]")
        print("-" * 40)
        
        app_id = input("Enter the ID of the appointment you want to delete: ").strip()
        
        cursor.execute('''
            DELETE FROM appointments 
            WHERE id = ? AND client_name = ?
        ''', (app_id, search_name))
        
        if cursor.rowcount > 0:
            conn.commit()
            print("Appointment deleted successfully!")
        else:
            print("Error: ID not found or doesn't match the client name.")
            
    conn.close()

def view_appointments():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM appointments')
    rows = cursor.fetchall()
    print("\n--- All Appointments ---")
    if len(rows) == 0:
        print("No appointments booked yet.")
    else:
        for row in rows:
            print(f"ID: {row[0]} | Name: {row[1]} | Service: {row[2]} | Date: {row[3]} | Time: {row[4]} | Status: [{row[5]}]")
    print("-" * 40)
    conn.close()