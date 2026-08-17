import db_manager

def main():
    # יצירת בסיס הנתונים והטבלה בהרצה ראשונה
    db_manager.init_db()
    print("Hello, you got to Yarin Barber Shop!")
    
    while True:
        print("\n=== YARIN BARBER SHOP - MENU ===")
        print("1. Book an appointment (קביעת תור)")
        print("2. View all appointments (צפייה בתורים)")
        print("3. Update appointment status (עדכון סטטוס תור)")
        print("4. Delete an appointment (מחיקת תור)")
        print("5. Exit (יציאה)")
        
        choice = input("Choose an option (1-5): ").strip()
        
        if choice == '1':
            name = input("What's your name? ").strip()
            service = input("What are we doing? (e.g., Haircut/Beard): ").strip()
            date = input("Enter appointment date (e.g., DD/MM/YYYY): ").strip()
            time = input("Enter appointment time (e.g., 10:00): ").strip()
            
            # בדיקת תקינות קלט בסיסית - מוודאים שלא הוכנסו שדות ריקים
            if name != "" and service != "" and date != "" and time != "":
                db_manager.add_appointment(name, service, date, time)
            else:
                print("Error: All fields are required!")
                
        elif choice == '2':
            db_manager.view_appointments()
            
        elif choice == '3':
            db_manager.update_status_by_name()
            
        elif choice == '4':
            db_manager.delete_appointment_by_name()
            
        elif choice == '5':
            print("Goodbye! See you next time at Yarin Barber Shop.")
            break
        else:
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    main()