import decimal
from datetime import datetime
import configparser
import mysql.connector
from mysql.connector import Error
from flask import Flask, render_template, request, redirect, url_for, session, flash
from decimal import Decimal

app = Flask(__name__, template_folder='/usr/local/templates')
app.secret_key = 'your_secret_key'


def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config


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
        else:
            print("Nie udało się nawiązać połączenia z bazą danych.")
            return None
    except Error as e:
        print(f"Błąd podczas łączenia z MySQL: {e}")
        return None


def execute_query(query, params=()):
    connection = create_connection()
    if connection is None:
        flash("Nie udało się połączyć z bazą danych.", 'danger')
        return False
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(query, params)
        connection.commit()
        return True
    except Error as e:
        print(f"Błąd podczas wykonywania zapytania: {e}")
        flash(f"Wystąpił błąd podczas wykonywania operacji. Szczegóły: {e}", 'danger')
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def fetch_query(query, params=()):
    connection = create_connection()
    if connection is None:
        flash("Nie udało się połączyć z bazą danych.", 'danger')
        return []
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        result = cursor.fetchall()
        return result
    except Error as e:
        print(f"Błąd podczas pobierania danych: {e}")
        flash("Wystąpił błąd podczas pobierania danych.", 'danger')
        return []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/check_db')
def check_db():
    try:
        connection = create_connection()
        if connection and connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            if result:
                return "Połączenie z bazą danych działa poprawnie!", 200
        return "Nie udało się połączyć z bazą danych.", 500
    except Exception as e:
        return f"Błąd połączenia z bazą danych: {e}", 500


@app.route('/')
def index():
    return render_template('index.html')


def fetch_user_by_email_and_password(email, password):
    query = "SELECT * FROM users WHERE Email = %s AND Haslo = %s"
    return fetch_query(query, (email, password))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = fetch_user_by_email_and_password(email, password)
        if user:
            session['user'] = user[0]
            flash(f"Zalogowano jako {user[0]['Rola']}", 'success')
            return redirect(url_for('index'))
        else:
            flash("Nieprawidłowy email lub hasło", 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Wylogowano pomyślnie", 'success')
    return redirect(url_for('index'))


def add_user(imie, nazwisko, email, haslo, rola, data_urodzenia):
    query = """INSERT INTO users (Imie, Nazwisko, Email, Haslo, Rola, DataUrodzenia) 
               VALUES (%s, %s, %s, %s, %s, %s)"""
    return execute_query(query, (imie, nazwisko, email, haslo, rola, data_urodzenia))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        imie = request.form['imie']
        nazwisko = request.form['nazwisko']
        email = request.form['email']
        haslo = request.form['haslo']
        data_urodzenia = request.form['data_urodzenia']
        rola = 'klient'  # domyślna rola dla nowego użytkownika

        if not (imie and nazwisko and email and haslo and data_urodzenia):
            flash("Wszystkie pola są wymagane", 'danger')
        else:
            try:
                add_user(imie, nazwisko, email, haslo, rola, data_urodzenia)
                flash("Zarejestrowano pomyślnie", 'success')
                return redirect(url_for('login'))
            except Exception as e:
                print(f"Błąd: {e}")
                flash(f"Wystąpił błąd podczas rejestracji. Szczegóły: {e}", 'danger')

    return render_template('register.html')


def add_event_with_check(nazwa, data, miejsce_id, opis, limit_miejsc, cena, organizer_id):
    connection = create_connection()
    if connection is None:
        flash("Nie udało się połączyć z bazą danych.", 'danger')
        return False
    cursor = None
    try:
        cursor = connection.cursor()
        query_check = "SELECT COUNT(*) FROM events WHERE Data = %s AND MiejsceID = %s"
        cursor.execute(query_check, (data, miejsce_id))
        event_count = cursor.fetchone()[0]
        if event_count > 0:
            flash("Wydarzenie już istnieje dla tej daty i lokalizacji.", 'danger')
            return False
        else:
            query_insert = """INSERT INTO events (NazwaWydarzenia, Data, MiejsceID, Opis, LimitMiejsc, Cena, OrganizerID) 
                              VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(query_insert, (nazwa, data, miejsce_id, opis, limit_miejsc, cena, organizer_id))
            connection.commit()
            return True
    except Error as e:
        print(f"Błąd podczas dodawania wydarzenia: {e}")
        flash(f"Wystąpił błąd podczas dodawania wydarzenia. Szczegóły: {e}", 'danger')
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def delete_event(event_id):
    query = "DELETE FROM events WHERE EventID = %s"
    return execute_query(query, (event_id,))


def update_event(event_id, nazwa, data, miejsce_id, opis, limit_miejsc, cena):
    query = """UPDATE events SET NazwaWydarzenia = %s, Data = %s, MiejsceID = %s, Opis = %s, 
               LimitMiejsc = %s, Cena = %s WHERE EventID = %s"""
    return execute_query(query, (nazwa, data, miejsce_id, opis, limit_miejsc, cena, event_id))


def get_events():
    query = "SELECT * FROM events"
    return fetch_query(query)


def get_locations():
    query = "SELECT * FROM location"
    return fetch_query(query)


def get_categories():
    query = "SELECT * FROM eventcategories"
    return fetch_query(query)


@app.route('/manage_events', methods=['GET', 'POST'])
def manage_events():
    if 'user' not in session or session['user']['Rola'] != 'administrator':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        action = request.form['action']
        if action == 'add':
            nazwa = request.form['nazwa']
            data = request.form['data']
            miejsce_id = request.form['miejsce_id']
            opis = request.form['opis']
            limit_miejsc = request.form['limit_miejsc']
            cena = request.form['cena']
            organizer_id = session['user']['UserID']
            if not (nazwa and data and miejsce_id and opis and limit_miejsc and cena):
                flash("Wszystkie pola są wymagane", 'danger')
            else:
                try:
                    add_event_with_check(nazwa, data, miejsce_id, opis, limit_miejsc, cena, organizer_id)
                    flash("Wydarzenie dodane pomyślnie", 'success')
                except Exception as e:
                    flash(f"Błąd: {str(e)}", 'danger')
        elif action == 'delete':
            event_id = request.form['event_id']
            delete_event(event_id)
            flash("Wydarzenie usunięte pomyślnie", 'success')
        elif action == 'update':
            event_id = request.form['event_id']
            nazwa = request.form['nazwa']
            data = request.form['data']
            miejsce_id = request.form['miejsce_id']
            opis = request.form['opis']
            limit_miejsc = request.form['limit_miejsc']
            cena = request.form['cena']
            if not (nazwa and data and miejsce_id and opis and limit_miejsc and cena):
                flash("Wszystkie pola są wymagane", 'danger')
            else:
                update_event(event_id, nazwa, data, miejsce_id, opis, limit_miejsc, cena)
                flash("Wydarzenie zaktualizowane pomyślnie", 'success')
    events = get_events()
    locations = get_locations()
    categories = get_categories()
    return render_template('manage_events.html', events=events, locations=locations, categories=categories)


@app.route('/organizer_dashboard')
def organizer_dashboard():
    if 'user' not in session or session['user']['Rola'] != 'organizator':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    return render_template('organizer_dashboard.html')


@app.route('/organizer_events', methods=['GET', 'POST'])
def organizer_events():
    if 'user' not in session or session['user']['Rola'] != 'organizator':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        action = request.form['action']
        if action == 'add':
            nazwa = request.form['nazwa']
            data = request.form['data']
            miejsce_id = request.form['miejsce_id']
            opis = request.form['opis']
            limit_miejsc = request.form['limit_miejsc']
            cena = request.form['cena']
            organizer_id = session['user']['UserID']
            if not (nazwa and data and miejsce_id and opis and limit_miejsc and cena):
                flash("Wszystkie pola są wymagane", 'danger')
            else:
                try:
                    add_event_with_check(nazwa, data, miejsce_id, opis, limit_miejsc, cena, organizer_id)
                    flash("Wydarzenie dodane pomyślnie", 'success')
                except Exception as e:
                    flash(f"Błąd: {str(e)}", 'danger')
        elif action == 'delete':
            event_id = request.form['event_id']
            delete_event(event_id)
            flash("Wydarzenie usunięte pomyślnie", 'success')
        elif action == 'update':
            event_id = request.form['event_id']
            nazwa = request.form['nazwa']
            data = request.form['data']
            miejsce_id = request.form['miejsce_id']
            opis = request.form['opis']
            limit_miejsc = request.form['limit_miejsc']
            cena = request.form['cena']
            if not (nazwa and data and miejsce_id and opis and limit_miejsc and cena):
                flash("Wszystkie pola są wymagane", 'danger')
            else:
                update_event(event_id, nazwa, data, miejsce_id, opis, limit_miejsc, cena)
                flash("Wydarzenie zaktualizowane pomyślnie", 'success')
    events = get_events()
    locations = get_locations()
    categories = get_categories()
    return render_template('organizer_events.html', events=events, locations=locations, categories=categories)


def get_bookings_by_organizer(organizer_id):
    query = """SELECT T.TicketID, T.UserID, T.EventID, T.DataZakupu, T.Status
               FROM tickets T
               JOIN events E ON T.EventID = E.EventID
               WHERE E.OrganizerID = %s"""
    return fetch_query(query, (organizer_id,))


@app.route('/organizer_bookings')
def organizer_bookings():
    if 'user' not in session or session['user']['Rola'] != 'organizator':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    try:
        bookings = get_bookings_by_organizer(session['user']['UserID'])
        return render_template('organizer_bookings.html', bookings=bookings)
    except Exception as e:
        print(f"Błąd: {e}")
        flash(f"Wystąpił błąd podczas pobierania danych. Szczegóły: {e}", 'danger')
        return render_template('organizer_bookings.html', bookings=[])


def get_user_by_id(user_id):
    query = "SELECT * FROM users WHERE UserID = %s"
    result = fetch_query(query, (user_id,))
    return result[0] if result else None


def update_user(user_id, imie, nazwisko, email, haslo):
    query = """UPDATE users SET Imie = %s, Nazwisko = %s, Email = %s, Haslo = %s
               WHERE UserID = %s"""
    return execute_query(query, (imie, nazwisko, email, haslo, user_id))


@app.route('/organizer_profile', methods=['GET', 'POST'])
    # ... [kod bez zmian]
