import decimal
from datetime import datetime
import configparser
import mysql.connector
from mysql.connector import Error
from flask import Flask, render_template, request, redirect, url_for, session, flash
from decimal import Decimal

app = Flask(__name__, template_folder='/usr/local/templates')
app.secret_key = 'your_secret_key'  # Zmień na unikalny klucz i przechowuj w zmiennych środowiskowych

# Funkcja do ładowania konfiguracji
def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config

# Funkcja do tworzenia połączenia z bazą danych
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
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None

# Funkcja do wykonywania procedur składowanych bez wyniku zwracanego
def execute_stored_procedure(proc_name, params=()):
    connection = create_connection()
    if connection is None:
        flash("Nie udało się połączyć z bazą danych.", 'danger')
        return
    try:
        cursor = connection.cursor()
        cursor.callproc(proc_name, params)
        connection.commit()
    except Error as e:
        print(f"Error executing stored procedure {proc_name}: {e}")
        flash(f"Wystąpił błąd podczas wykonywania operacji. Szczegóły: {e}", 'danger')
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Funkcja do pobierania danych z procedur składowanych
def fetch_stored_procedure(proc_name, params=()):
    connection = create_connection()
    if connection is None:
        flash("Nie udało się połączyć z bazą danych.", 'danger')
        return []
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.callproc(proc_name, params)
        result = []
        for res in cursor.stored_results():
            result.extend(res.fetchall())
        return result
    except Error as e:
        print(f"Error fetching stored procedure {proc_name}: {e}")
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = fetch_stored_procedure('GetUser', (email, password))
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        imie = request.form['imie']
        nazwisko = request.form['nazwisko']
        email = request.form['email']
        haslo = request.form['haslo']
        data_urodzenia = request.form['data_urodzenia']
        rola = 'klient'
        if not (imie and nazwisko and email and haslo and data_urodzenia):
            flash("Wszystkie pola są wymagane", 'danger')
        else:
            try:
                execute_stored_procedure('AddUser', (imie, nazwisko, email, haslo, rola, data_urodzenia))
                flash("Zarejestrowano pomyślnie", 'success')
                return redirect(url_for('login'))
            except Exception as e:
                print(f"Error: {e}")
                flash(f"Wystąpił błąd podczas rejestracji. Szczegóły: {e}", 'danger')
    return render_template('register.html')

@app.route('/make_payment', methods=['GET', 'POST'])
def make_payment():
    if 'user' not in session or session['user']['Rola'] != 'klient':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        user_id = session['user']['UserID']
        ticket_id = request.form.get('ticket_id')
        metoda_platnosci = request.form.get('metoda_platnosci')
        if not ticket_id or not metoda_platnosci:
            flash("Wszystkie pola są wymagane", 'danger')
            return redirect(url_for('make_payment'))
        try:
            kwota = Decimal(request.form.get('kwota', '0'))
        except decimal.InvalidOperation:
            flash("Nieprawidłowa wartość kwoty", 'danger')
            return redirect(url_for('make_payment'))
        try:
            user_details = fetch_stored_procedure('GetUserDetails', (user_id,))
            if not user_details:
                flash("Nie znaleziono szczegółów użytkownika", 'danger')
                return redirect(url_for('index'))
            user_details = user_details[0]
            birth_date = user_details.get('DataUrodzenia')
            final_price = calculate_discounted_price(kwota, birth_date)
            execute_stored_procedure('MakePayment', (user_id, ticket_id, final_price, metoda_platnosci))
            flash("Płatność zakończona pomyślnie", 'success')
        except Exception as e:
            print(f"Błąd podczas wykonywania płatności: {e}")
            flash(f"Wystąpił błąd podczas wykonywania płatności. Szczegóły: {e}", 'danger')
        return redirect(url_for('book_event'))

    try:
        user_id = session['user']['UserID']
        tickets = fetch_stored_procedure('GetTicketsByUser', (user_id,))
        if not tickets:
            flash("Nie znaleziono dostępnych biletów", 'warning')
    except Exception as e:
        print(f"Błąd podczas pobierania biletów użytkownika: {e}")
        flash("Wystąpił błąd podczas pobierania biletów użytkownika", 'danger')
        tickets = []

    return render_template('make_payment.html', tickets=tickets)

def calculate_discounted_price(price, birth_date):
    today = datetime.today()
    if not isinstance(birth_date, datetime):
        raise ValueError("Nieprawidłowy format daty urodzenia")
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    discount = Decimal('0.2') if age < 25 or age > 70 else Decimal('0')
    return price * (Decimal('1') - discount)

def main():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
