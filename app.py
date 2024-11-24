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
        # Ustawienia połączenia
        connection = mysql.connector.connect(
            host="dev-mysql-primary.database.svc.cluster.local",
            user="root",
            password="admin",
            database="dev_db"
        )
        # Sprawdzenie połączenia
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"Połączono z bazą danych. Wersja serwera MySQL: {db_info}")
            return connection
        else:
            print("Nie udało się nawiązać połączenia z bazą danych.")
            return None
    except Error as e:
        # Obsługa specyficznych błędów MySQL
        if e.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            print("Błąd autoryzacji: nieprawidłowa nazwa użytkownika lub hasło.")
        elif e.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            print("Błąd: Nie znaleziono wskazanej bazy danych.")
        elif e.errno == mysql.connector.errorcode.CR_SERVER_LOST:
            print("Błąd: Utracono połączenie z serwerem.")
        elif e.errno == mysql.connector.errorcode.CR_CONN_HOST_ERROR:
            print("Błąd: Nie udało się połączyć z serwerem MySQL.")
        else:
            print(f"Niespodziewany błąd: {e}")
        return None
    except Exception as e:
        # Obsługa innych wyjątków
        print(f"Niespodziewany błąd aplikacji: {e}")
        return None


def execute_stored_procedure(proc_name, params=()):
    connection = create_connection()
    if connection is None:
        flash("Nie udało się połączyć z bazą danych.", 'danger')
        return False  # Zwracamy False, jeśli połączenie nie zostało ustanowione
    
    try:
        cursor = connection.cursor()
        cursor.callproc(proc_name, params)
        connection.commit()
        return True  # Zwracamy True, jeśli procedura zakończyła się sukcesem
    except mysql.connector.Error as e:
        error_message = f"Błąd SQL [{e.errno}]: {e.msg}"
        print(error_message)
        flash(f"Wystąpił błąd podczas wykonywania procedury {proc_name}. Szczegóły: {e.msg}", 'danger')
        return False  # Zwracamy False w przypadku błędu
    finally:
        if 'cursor' in locals() and cursor:  # Upewniamy się, że `cursor` istnieje
            cursor.close()
        if connection:
            connection.close()



def fetch_stored_procedure(proc_name, params=()):
    connection = create_connection()
    if connection is None:
        flash("Nie udało się połączyć z bazą danych.", 'danger')
        return []  # Zwracamy pustą listę w przypadku braku połączenia
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.callproc(proc_name, params)
        results = []
        for result in cursor.stored_results():
            results.extend(result.fetchall())
        return results
    except mysql.connector.Error as e:
        error_message = f"Błąd SQL [{e.errno}]: {e.msg}"
        print(f"{error_message} podczas wywołania procedury {proc_name} z parametrami {params}")
        flash(f"Wystąpił błąd podczas pobierania danych z procedury {proc_name}. Szczegóły: {e.msg}", 'danger')
        return []  # Zwracamy pustą listę w przypadku błędu
    finally:
        if 'cursor' in locals() and cursor:  # Upewniamy się, że `cursor` istnieje
            cursor.close()
        if connection:
            connection.close()

        
@app.route('/check_db')
def check_db():
    connection = None
    cursor = None
    try:
        # Testowe połączenie z bazą danych
        connection = create_connection()
        if connection and connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT 1")  # Proste zapytanie testowe
            result = cursor.fetchone()
            if result:
                return "Połączenie z bazą danych działa poprawnie!", 200
        return "Nie udało się połączyć z bazą danych.", 500
    except mysql.connector.Error as e:
        error_message = f"Błąd podczas łączenia z bazą danych: {e}"
        print(error_message)
        return error_message, 500
    except Exception as e:
        print(f"Niespodziewany błąd: {e}")
        return f"Błąd połączenia z bazą danych: {e}", 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()



@app.route('/')
def index():
    return render_template('index.html')


from flask import Flask, request, session, redirect, url_for, flash, render_template
from werkzeug.security import check_password_hash

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Wszystkie pola są wymagane", 'danger')
            return render_template('login.html')

        try:
            # Pobierz dane użytkownika z bazy danych
            user = fetch_stored_procedure('GetUser', (email,))
            if user:
                user = user[0]  # Zakładamy, że `fetch_stored_procedure` zwraca listę rekordów
                if check_password_hash(user['Haslo'], password):  # Weryfikacja hasła
                    session['user'] = {
                        'UserID': user['UserID'],
                        'Email': user['Email'],
                        'Rola': user['Rola']
                    }
                    flash(f"Zalogowano jako {user['Rola']}", 'success')
                    return redirect(url_for('index'))
                else:
                    flash("Nieprawidłowe hasło", 'danger')
            else:
                flash("Nie znaleziono użytkownika z podanym adresem email", 'danger')
        except Exception as e:
            flash(f"Wystąpił błąd podczas logowania: {e}", 'danger')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Wylogowano pomyślnie", 'success')
    return redirect(url_for('index'))


from werkzeug.security import generate_password_hash
import re

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Pobierz dane z formularza
        imie = request.form.get('imie')
        nazwisko = request.form.get('nazwisko')
        email = request.form.get('email')
        haslo = request.form.get('haslo')
        data_urodzenia = request.form.get('data_urodzenia')
        rola = 'klient'  # domyślna rola

        # Walidacja danych
        if not all([imie, nazwisko, email, haslo, data_urodzenia]):
            flash("Wszystkie pola są wymagane", 'danger')
            return render_template('register.html')

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Nieprawidłowy format adresu email", 'danger')
            return render_template('register.html')

        if len(haslo) < 8:
            flash("Hasło musi mieć co najmniej 8 znaków", 'danger')
            return render_template('register.html')

        # Hashowanie hasła
        hashed_password = generate_password_hash(haslo)

        try:
            # Sprawdź, czy email już istnieje
            existing_user = fetch_stored_procedure('GetUserByEmail', (email,))
            if existing_user:
                flash("Adres email jest już zarejestrowany", 'danger')
                return render_template('register.html')

            # Dodanie użytkownika
            execute_stored_procedure('AddUser', (imie, nazwisko, email, hashed_password, rola, data_urodzenia))
            flash("Zarejestrowano pomyślnie", 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error: {e}")
            flash(f"Wystąpił błąd podczas rejestracji. Szczegóły: {e}", 'danger')

    return render_template('register.html')



@app.route('/manage_events', methods=['GET', 'POST'])
def manage_events():
    # Sprawdzenie, czy użytkownik ma uprawnienia administratora
    if 'user' not in session or session['user']['Rola'] != 'administrator':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'add':
                # Pobranie i walidacja danych z formularza
                nazwa = request.form.get('nazwa')
                data = request.form.get('data')
                miejsce_id = request.form.get('miejsce_id', type=int)
                opis = request.form.get('opis')
                limit_miejsc = request.form.get('limit_miejsc', type=int)
                cena = request.form.get('cena', type=float)
                organizer_id = session['user']['UserID']

                if not all([nazwa, data, miejsce_id, opis, limit_miejsc, cena]):
                    flash("Wszystkie pola są wymagane", 'danger')
                elif limit_miejsc <= 0 or cena <= 0:
                    flash("Limit miejsc i cena muszą być większe niż 0", 'danger')
                else:
                    execute_stored_procedure('AddEventWithCheck', (nazwa, data, miejsce_id, opis, limit_miejsc, cena, organizer_id))
                    flash("Wydarzenie dodane pomyślnie", 'success')

            elif action == 'delete':
                # Usunięcie wydarzenia
                event_id = request.form.get('event_id', type=int)
                if not event_id:
                    flash("ID wydarzenia jest wymagane", 'danger')
                else:
                    execute_stored_procedure('DeleteEvent', (event_id,))
                    flash("Wydarzenie usunięte pomyślnie", 'success')

            elif action == 'update':
                # Aktualizacja wydarzenia
                event_id = request.form.get('event_id', type=int)
                nazwa = request.form.get('nazwa')
                data = request.form.get('data')
                miejsce_id = request.form.get('miejsce_id', type=int)
                opis = request.form.get('opis')
                limit_miejsc = request.form.get('limit_miejsc', type=int)
                cena = request.form.get('cena', type=float)

                if not all([event_id, nazwa, data, miejsce_id, opis, limit_miejsc, cena]):
                    flash("Wszystkie pola są wymagane", 'danger')
                elif limit_miejsc <= 0 or cena <= 0:
                    flash("Limit miejsc i cena muszą być większe niż 0", 'danger')
                else:
                    execute_stored_procedure('UpdateEvent', (event_id, nazwa, data, miejsce_id, opis, limit_miejsc, cena))
                    flash("Wydarzenie zaktualizowane pomyślnie", 'success')

        except Exception as e:
            print(f"Błąd: {e}")
            flash(f"Wystąpił błąd: {e}", 'danger')

    # Pobieranie danych do wyświetlenia na stronie
    try:
        events = fetch_stored_procedure('GetEvents')
        locations = fetch_stored_procedure('GetLocations')
        categories = fetch_stored_procedure('GetCategories')
    except Exception as e:
        flash(f"Błąd podczas pobierania danych: {e}", 'danger')
        events, locations, categories = [], [], []

    return render_template('manage_events.html', events=events, locations=locations, categories=categories)


@app.route('/organizer_dashboard')
def organizer_dashboard():
    if 'user' not in session or session['user']['Rola'] != 'organizator':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    return render_template('organizer_dashboard.html')


@app.route('/organizer_events', methods=['GET', 'POST'])
def organizer_events():
    # Sprawdzenie, czy użytkownik jest organizatorem
    if 'user' not in session or session['user']['Rola'] != 'organizator':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    
    try:
        organizer_id = session['user']['UserID']
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'add':
                # Dodawanie wydarzenia
                nazwa = request.form.get('nazwa')
                data = request.form.get('data')
                miejsce_id = request.form.get('miejsce_id', type=int)
                opis = request.form.get('opis')
                limit_miejsc = request.form.get('limit_miejsc', type=int)
                cena = request.form.get('cena', type=float)

                if not all([nazwa, data, miejsce_id, opis, limit_miejsc, cena]):
                    flash("Wszystkie pola są wymagane", 'danger')
                elif limit_miejsc <= 0 or cena <= 0:
                    flash("Limit miejsc i cena muszą być większe niż 0", 'danger')
                else:
                    execute_stored_procedure('AddEventWithCheck', (nazwa, data, miejsce_id, opis, limit_miejsc, cena, organizer_id))
                    flash("Wydarzenie dodane pomyślnie", 'success')

            elif action == 'delete':
                # Usuwanie wydarzenia
                event_id = request.form.get('event_id', type=int)
                if not event_id:
                    flash("ID wydarzenia jest wymagane", 'danger')
                else:
                    execute_stored_procedure('DeleteEvent', (event_id,))
                    flash("Wydarzenie usunięte pomyślnie", 'success')

            elif action == 'update':
                # Aktualizacja wydarzenia
                event_id = request.form.get('event_id', type=int)
                nazwa = request.form.get('nazwa')
                data = request.form.get('data')
                miejsce_id = request.form.get('miejsce_id', type=int)
                opis = request.form.get('opis')
                limit_miejsc = request.form.get('limit_miejsc', type=int)
                cena = request.form.get('cena', type=float)

                if not all([event_id, nazwa, data, miejsce_id, opis, limit_miejsc, cena]):
                    flash("Wszystkie pola są wymagane", 'danger')
                elif limit_miejsc <= 0 or cena <= 0:
                    flash("Limit miejsc i cena muszą być większe niż 0", 'danger')
                else:
                    execute_stored_procedure('UpdateEvent', (event_id, nazwa, data, miejsce_id, opis, limit_miejsc, cena))
                    flash("Wydarzenie zaktualizowane pomyślnie", 'success')

        # Pobieranie wydarzeń, które stworzył organizator
        events = fetch_stored_procedure('GetEventsByOrganizer', (organizer_id,))
        locations = fetch_stored_procedure('GetLocations')
        categories = fetch_stored_procedure('GetCategories')

        return render_template('organizer_events.html', events=events, locations=locations, categories=categories)

    except Exception as e:
        print(f"Błąd: {e}")
        flash(f"Wystąpił błąd: {e}", 'danger')
        return redirect(url_for('index'))

@app.route('/organizer_bookings')
def organizer_bookings():
    # Sprawdzanie, czy użytkownik ma rolę organizatora
    if 'user' not in session or session['user']['Rola'] != 'organizator':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    
    try:
        # Pobranie ID użytkownika organizatora z sesji
        organizer_id = session['user']['UserID']

        # Pobieranie danych rezerwacji dla organizatora
        bookings = fetch_stored_procedure('GetBookingsByOrganizer', (organizer_id,))
        
        if not bookings:
            flash("Brak rezerwacji dla Twoich wydarzeń.", 'info')
        
        return render_template('organizer_bookings.html', bookings=bookings)

    except Exception as e:
        print(f"Błąd podczas pobierania rezerwacji: {e}")
        flash(f"Wystąpił błąd podczas pobierania danych. Szczegóły: {e}", 'danger')
        return render_template('organizer_bookings.html', bookings=[])


@app.route('/organizer_profile', methods=['GET', 'POST'])
def organizer_profile():
    if 'user' not in session or session['user']['Rola'] != 'organizator':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    user = fetch_stored_procedure('GetUserById', (session['user']['UserID'],))[0]
    if request.method == 'POST':
        imie = request.form['imie']
        nazwisko = request.form['nazwisko']
        email = request.form['email']
        haslo = request.form['haslo']
        if not (imie and nazwisko and email):
            flash("Wszystkie pola są wymagane", 'danger')
        else:
            execute_stored_procedure('UpdateUser', (session['user']['UserID'], imie, nazwisko, email, haslo))
            flash("Profil zaktualizowany pomyślnie", 'success')
            return redirect(url_for('organizer_dashboard'))
    return render_template('organizer_profile.html', user=user)


@app.route('/book_event', methods=['GET', 'POST'])
def book_event():
    if 'user' not in session or session['user']['Rola'] != 'klient':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    events = fetch_stored_procedure('GetEvents')
    if request.method == 'POST':
        user_id = session['user']['UserID']
        event_id = request.form['event_id']
        status = 'aktywny'
        znizka_id = request.form.get('znizka_id')
        if not (user_id and event_id):
            flash("UserID i EventID są wymagane", 'danger')
        else:
            try:
                execute_stored_procedure('BookTicket', (user_id, event_id, status, znizka_id if znizka_id else None))
                flash("Zarezerwowano pomyślnie", 'success')
            except Exception as e:
                print(f"Error: {e}")
                flash(f"Wystąpił błąd podczas wykonywania operacji. Szczegóły: {e}", 'danger')
    return render_template('book_event.html', events=events)



def calculate_discounted_price(price, birth_date):
    if birth_date is None:
        flash("Data urodzenia użytkownika jest nieznana. Zniżka nie zostanie zastosowana.", 'warning')
        return price
    try:
        today = datetime.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        discount = Decimal('0.2') if age < 25 or age > 70 else Decimal('0')
        return price * (Decimal('1') - discount)
    except Exception as e:
        print(f"Błąd podczas obliczania zniżki: {e}")
        return price



@app.route('/make_payment', methods=['GET', 'POST'])
def make_payment():
    if 'user' not in session or session['user']['Rola'] != 'klient':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        user_id = session['user']['UserID']
        ticket_id = request.form.get('ticket_id')
        kwota_raw = request.form.get('kwota')
        metoda_platnosci = request.form.get('metoda_platnosci')

        # Walidacja danych wejściowych
        if not user_id or not ticket_id or not kwota_raw or not metoda_platnosci:
            flash("Wszystkie pola są wymagane.", 'danger')
            return redirect(url_for('make_payment'))

        try:
            kwota = Decimal(kwota_raw)
        except decimal.InvalidOperation:
            flash("Nieprawidłowa wartość kwoty.", 'danger')
            return redirect(url_for('make_payment'))

        # Pobierz szczegóły użytkownika
        user_details = fetch_stored_procedure('GetUserDetails', (user_id,))
        if not user_details or 'DataUrodzenia' not in user_details[0]:
            flash("Nie znaleziono szczegółów użytkownika lub brakuje daty urodzenia.", 'danger')
            return redirect(url_for('make_payment'))

        birth_date = user_details[0]['DataUrodzenia']
        final_price = calculate_discounted_price(kwota, birth_date)

        try:
            execute_stored_procedure('MakePayment', (user_id, ticket_id, final_price, metoda_platnosci))
            flash("Płatność zakończona pomyślnie.", 'success')
        except Exception as e:
            print(f"Błąd podczas płatności: {e}")
            flash(f"Wystąpił błąd podczas płatności. Szczegóły: {e}", 'danger')
        return redirect(url_for('book_event'))

    # Pobranie biletów dla użytkownika
    user_id = session['user']['UserID']
    tickets = fetch_stored_procedure('GetTicketsByUser', (user_id,))
    if not tickets:
        flash("Nie znaleziono biletów dla tego użytkownika.", 'warning')

    return render_template('make_payment.html', tickets=tickets)



@app.route('/filter_events', methods=['GET', 'POST'])
def filter_events():
    if 'user' not in session or session['user']['Rola'] != 'klient':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))

    events = []
    if request.method == 'POST':
        try:
            category = request.form.get('category') or None
            city = request.form.get('city') or None
            country = request.form.get('country') or None
            date_from = request.form.get('date_from') or None
            date_to = request.form.get('date_to') or None
            capacity_min = int(request.form.get('capacity_min')) if request.form.get('capacity_min') else None
            capacity_max = int(request.form.get('capacity_max')) if request.form.get('capacity_max') else None
            seat_type = request.form.get('seat_type') or None
            price_min = Decimal(request.form.get('price_min')) if request.form.get('price_min') else None
            price_max = Decimal(request.form.get('price_max')) if request.form.get('price_max') else None
            available_only = request.form.get('available_only') == 'on'

            events = fetch_stored_procedure('FilterEvents', (
                category, f"%{city}%", f"%{country}%", date_from, date_to,
                capacity_min, capacity_max, f"%{seat_type}%", price_min, price_max, available_only
            ))
        except Exception as e:
            print(f"Błąd podczas filtrowania wydarzeń: {e}")
            flash("Wystąpił błąd podczas filtrowania wydarzeń.", 'danger')

    categories = fetch_stored_procedure('GetCategories')
    return render_template('filter_events.html', events=events, categories=categories)



@app.route('/reports')
def reports():
    return render_template('reports.html')


@app.route('/report/events_per_category')
def report_events_per_category():
    results = fetch_stored_procedure('ReportEventsPerCategory')
    return render_template('report.html', title="Liczba wydarzeń w poszczególnych kategoriach", results=results)


@app.route('/report/average_rating_per_category')
def report_average_rating_per_category():
    results = fetch_stored_procedure('ReportAverageRatingPerCategory')
    return render_template('report.html', title="Średnia ocena wydarzeń w poszczególnych kategoriach", results=results)


@app.route('/report/top_selling_events')
def report_top_selling_events():
    results = fetch_stored_procedure('ReportTopSellingEvents')
    return render_template('report.html', title="Najczęściej kupowane bilety w poszczególnych kategoriach", results=results)


@app.route('/report/most_rated_events')
def report_most_rated_events():
    results = fetch_stored_procedure('ReportMostRatedEvents')
    return render_template('report.html', title="Najczęściej oceniane wydarzenia", results=results)


@app.route('/report/event_revenue')
def report_event_revenue():
    results = fetch_stored_procedure('ReportEventRevenue')
    return render_template('report.html', title="Suma wpływów z poszczególnych wydarzeń", results=results)


@app.route('/report/revenue_in_period', methods=['GET', 'POST'])
def report_revenue_in_period():
    results = []
    if request.method == 'POST':
        date_from = request.form['date_from']
        date_to = request.form['date_to']
        results = fetch_stored_procedure('ReportRevenueInPeriod', (date_from, date_to))
    return render_template('report_revenue_in_period.html', title="Suma wpływów z wydarzeń w danym okresie", results=results)
    
def main():
    app.run(host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
