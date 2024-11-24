from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from decimal import Decimal
from datetime import datetime

app = Flask(__name__, template_folder='/usr/local/templates')
app.secret_key = 'your_secret_key'


# Helper functions for database operations
def create_connection():
    try:
        connection = mysql.connector.connect(
            host="dev-mysql-primary.database.svc.cluster.local",
            user="root",
            password="admin",
            database="dev_db"
        )
        if connection.is_connected():
            return connection
        return None
    except mysql.connector.Error as e:
        print(f"Błąd: {e}")
        return None


def execute_query(query, params=()):
    connection = create_connection()
    if not connection:
        return False
    try:
        cursor = connection.cursor()
        cursor.execute(query, params)
        connection.commit()
        return True
    except mysql.connector.Error as e:
        print(f"Błąd SQL: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def fetch_query(query, params=()):
    connection = create_connection()
    if not connection:
        return []
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        results = cursor.fetchall()
        return results
    except mysql.connector.Error as e:
        print(f"Błąd SQL: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# Home page
@app.route('/')
def index():
    return render_template('index.html')


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        query = "SELECT * FROM Users WHERE Email = %s"
        user = fetch_query(query, (email,))
        if user:
            user = user[0]
            if user['Haslo'] == password:
                session['user'] = {
                    'UserID': user['UserID'],
                    'Email': user['Email'],
                    'Rola': user['Rola']
                }
                flash(f"Zalogowano jako {user['Rola']}", 'success')
                return redirect(url_for('index'))
            else:
                flash("Nieprawidłowe hasło.", 'danger')
        else:
            flash("Nie znaleziono użytkownika.", 'danger')
    return render_template('login.html')


# User logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Wylogowano pomyślnie.", 'success')
    return redirect(url_for('index'))


# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        imie = request.form.get('imie')
        nazwisko = request.form.get('nazwisko')
        email = request.form.get('email')
        haslo = request.form.get('haslo')
        data_urodzenia = request.form.get('data_urodzenia')

        query_check = "SELECT * FROM Users WHERE Email = %s"
        if fetch_query(query_check, (email,)):
            flash("Email jest już zarejestrowany.", 'danger')
            return render_template('register.html')

        query_insert = """
            INSERT INTO Users (Imie, Nazwisko, Email, Haslo, Rola, DataUrodzenia)
            VALUES (%s, %s, %s, %s, 'klient', %s)
        """
        if execute_query(query_insert, (imie, nazwisko, email, haslo, data_urodzenia)):
            flash("Rejestracja zakończona pomyślnie.", 'success')
            return redirect(url_for('login'))
        else:
            flash("Wystąpił błąd podczas rejestracji.", 'danger')
    return render_template('register.html')


# Manage events (admin functionality)
@app.route('/manage_events', methods=['GET', 'POST'])
def manage_events():
    if 'user' not in session or session['user']['Rola'] != 'administrator':
        flash("Brak dostępu.", 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'add':
                nazwa = request.form.get('nazwa')
                data = request.form.get('data')
                miejsce_id = request.form.get('miejsce_id')
                opis = request.form.get('opis')
                limit_miejsc = request.form.get('limit_miejsc')
                cena = request.form.get('cena')

                query = """
                    INSERT INTO Events (Nazwa, Data, MiejsceID, Opis, LimitMiejsc, Cena)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                execute_query(query, (nazwa, data, miejsce_id, opis, limit_miejsc, cena))
                flash("Wydarzenie dodane pomyślnie.", 'success')

            elif action == 'delete':
                event_id = request.form.get('event_id')
                query = "DELETE FROM Events WHERE EventID = %s"
                execute_query(query, (event_id,))
                flash("Wydarzenie usunięte pomyślnie.", 'success')

            elif action == 'update':
                event_id = request.form.get('event_id')
                nazwa = request.form.get('nazwa')
                data = request.form.get('data')
                miejsce_id = request.form.get('miejsce_id')
                opis = request.form.get('opis')
                limit_miejsc = request.form.get('limit_miejsc')
                cena = request.form.get('cena')

                query = """
                    UPDATE Events SET Nazwa = %s, Data = %s, MiejsceID = %s,
                    Opis = %s, LimitMiejsc = %s, Cena = %s WHERE EventID = %s
                """
                execute_query(query, (nazwa, data, miejsce_id, opis, limit_miejsc, cena, event_id))
                flash("Wydarzenie zaktualizowane pomyślnie.", 'success')
        except Exception as e:
            flash(f"Błąd: {e}", 'danger')

    events = fetch_query("SELECT * FROM Events")
    locations = fetch_query("SELECT * FROM Locations")
    categories = fetch_query("SELECT * FROM Categories")
    return render_template('manage_events.html', events=events, locations=locations, categories=categories)


# Booking events
@app.route('/book_event', methods=['GET', 'POST'])
def book_event():
    # Upewnij się, że użytkownik jest zalogowany i ma odpowiednią rolę
    if 'user' not in session or session['user']['Rola'] != 'klient':
        flash("Brak dostępu. Musisz być zalogowany jako klient.", 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Pobierz dane użytkownika i wydarzenia z formularza
        user_id = session['user']['UserID']
        event_id = request.form.get('event_id')

        # Sprawdź dostępność miejsc na wydarzenie
        event = fetch_query("SELECT LimitMiejsc FROM Events WHERE EventID = %s", (event_id,))
        if event:
            available_seats = event[0]['LimitMiejsc']
            if available_seats > 0:
                # Dodaj rezerwację do bazy danych
                status = 'aktywny'
                query_booking = """
                    INSERT INTO Bookings (UserID, EventID, Status)
                    VALUES (%s, %s, %s)
                """
                if execute_query(query_booking, (user_id, event_id, status)):
                    # Zmniejsz limit miejsc na wydarzeniu
                    query_update_seats = "UPDATE Events SET LimitMiejsc = LimitMiejsc - 1 WHERE EventID = %s"
                    execute_query(query_update_seats, (event_id,))
                    flash("Zarezerwowano pomyślnie.", 'success')
                else:
                    flash("Wystąpił błąd podczas rezerwacji.", 'danger')
            else:
                flash("Brak wolnych miejsc na to wydarzenie.", 'danger')
        else:
            flash("Nie znaleziono wybranego wydarzenia.", 'danger')

    # Pobierz dostępne wydarzenia (te, które mają wolne miejsca)
    events = fetch_query("SELECT * FROM Events WHERE LimitMiejsc > 0")
    return render_template('book_event.html', events=events)



# Generate reports
@app.route('/reports')
def reports():
    events_per_category = fetch_query("""
        SELECT Categories.Name AS Category, COUNT(*) AS EventCount
        FROM Events
        JOIN Categories ON Events.CategoryID = Categories.CategoryID
        GROUP BY Categories.Name
    """)
    return render_template('reports.html', reports={'events_per_category': events_per_category})


def main():
    app.run(host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
