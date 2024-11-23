import decimal
from datetime import datetime
import configparser
import mysql.connector
from mysql.connector import Error
from flask import Flask, render_template, request, redirect, url_for, session, flash
from decimal import Decimal

app = Flask(__name__, template_folder='/usr/local/templates')
app.secret_key = 'your_secret_key'  # Zmienny klucz dla bezpieczeństwa


# Funkcja do ładowania konfiguracji
def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config


# Funkcja do tworzenia połączenia z bazą danych
def create_connection():
    try:
        config = load_config()
        connection = mysql.connector.connect(
            host=config['database']['host'],
            user=config['database']['user'],
            password=config['database']['password'],
            database=config['database']['database']
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Błąd podczas łączenia z bazą danych: {e}")
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
        print(f"Błąd podczas wykonywania procedury składowanej {proc_name}: {e}")
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
        print(f"Błąd podczas pobierania danych z procedury składowanej {proc_name}: {e}")
        flash(f"Wystąpił błąd podczas pobierania danych. Szczegóły: {e}", 'danger')
        return []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            flash("Email i hasło są wymagane.", 'danger')
            return redirect(url_for('login'))
        try:
            user = fetch_stored_procedure('GetUser', (email, password))
            if user:
                session['user'] = user[0]
                flash(f"Zalogowano jako {user[0]['Rola']}", 'success')
                return redirect(url_for('index'))
            else:
                flash("Nieprawidłowy email lub hasło", 'danger')
        except Exception as e:
            flash(f"Wystąpił błąd logowania: {e}", 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Wylogowano pomyślnie", 'success')
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        imie = request.form.get('imie')
        nazwisko = request.form.get('nazwisko')
        email = request.form.get('email')
        haslo = request.form.get('haslo')
        data_urodzenia = request.form.get('data_urodzenia')
        rola = 'klient'

        if not all([imie, nazwisko, email, haslo, data_urodzenia]):
            flash("Wszystkie pola są wymagane.", 'danger')
            return redirect(url_for('register'))
        try:
            execute_stored_procedure('AddUser', (imie, nazwisko, email, haslo, rola, data_urodzenia))
            flash("Rejestracja przebiegła pomyślnie.", 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Wystąpił błąd podczas rejestracji: {e}", 'danger')
    return render_template('register.html')


@app.route('/make_payment', methods=['GET', 'POST'])
def make_payment():
    if 'user' not in session or session['user']['Rola'] != 'klient':
        flash("Brak dostępu.", 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        user_id = session['user']['UserID']
        ticket_id = request.form.get('ticket_id')
        metoda_platnosci = request.form.get('metoda_platnosci')

        if not ticket_id or not metoda_platnosci:
            flash("Wszystkie pola są wymagane.", 'danger')
            return redirect(url_for('make_payment'))
        try:
            kwota = Decimal(request.form.get('kwota', '0'))
        except decimal.InvalidOperation:
            flash("Nieprawidłowa wartość kwoty.", 'danger')
            return redirect(url_for('make_payment'))
        try:
            user_details = fetch_stored_procedure('GetUserDetails', (user_id,))
            if not user_details:
                flash("Nie znaleziono szczegółów użytkownika.", 'danger')
                return redirect(url_for('index'))
            birth_date = user_details[0].get('DataUrodzenia')
            final_price = calculate_discounted_price(kwota, birth_date)
            execute_stored_procedure('MakePayment', (user_id, ticket_id, final_price, metoda_platnosci))
            flash("Płatność zakończona pomyślnie.", 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Wystąpił błąd podczas płatności: {e}", 'danger')

    return render_template('make_payment.html')


def calculate_discounted_price(price, birth_date):
    today = datetime.today()
    if not birth_date:
        raise ValueError("Data urodzenia nie została podana.")
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    discount = Decimal('0.2') if age < 25 or age > 70 else Decimal('0')
    return price * (Decimal('1') - discount)


def main():
    app.run(host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
