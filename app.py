import decimal
from datetime import datetime
import configparser
import psycopg2
import psycopg2.extras
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
        connection = psycopg2.connect(
            host="postgres.database.svc.cluster.local",
            user="dev_user",
            password="dev",
            dbname="dev_db"
        )
        return connection
    except psycopg2.Error as e:
        print(f"Error while connecting to PostgreSQL: {e}")
        return None


def execute_function(func_name, params=()):
    connection = create_connection()
    if connection is None:
        flash("Nie udało się połączyć z bazą danych.", 'danger')
        return
    try:
        cursor = connection.cursor()
        placeholders = ", ".join(["%s"] * len(params))
        query = f"SELECT {func_name}({placeholders});" if params else f"SELECT {func_name}();"
        cursor.execute(query, params)
        connection.commit()
    except psycopg2.Error as e:
        print(f"Error executing function {func_name}: {e}")
        flash(f"Wystąpił błąd podczas wykonywania operacji. Szczegóły: {e}", 'danger')
    finally:
        cursor.close()
        connection.close()


def fetch_function(func_name, params=()):
    connection = create_connection()
    if connection is None:
        flash("Nie udało się połączyć z bazą danych.", 'danger')
        return []
    try:
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        placeholders = ", ".join(["%s"] * len(params))
        query = f"SELECT * FROM {func_name}({placeholders});" if params else f"SELECT * FROM {func_name}();"
        cursor.execute(query, params)
        result = cursor.fetchall()
        return result
    except psycopg2.Error as e:
        print(f"Error fetching function {func_name}: {e}")
        flash("Wystąpił błąd podczas pobierania danych.", 'danger')
        return []
    finally:
        cursor.close()
        connection.close()


@app.route('/check_db')
def check_db():
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT 1;")
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
        user = fetch_function('GetUser', (email, password))
        if user:
            session['user'] = user[0]
            flash(f"Zalogowano jako {user[0]['rola']}", 'success')
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
                execute_function('AddUser', (imie, nazwisko, email, haslo, rola, data_urodzenia))
                flash("Zarejestrowano pomyślnie", 'success')
                return redirect(url_for('login'))
            except Exception as e:
                print(f"Error: {e}")
                flash(f"Wystąpił błąd podczas rejestracji. Szczegóły: {e}", 'danger')
    return render_template('register.html')


@app.route('/manage_events', methods=['GET', 'POST'])
def manage_events():
    if 'user' not in session or session['user']['rola'] != 'administrator':
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
            organizer_id = session['user']['userid']
            if not (nazwa and data and miejsce_id and opis and limit_miejsc and cena):
                flash("Wszystkie pola są wymagane", 'danger')
            else:
                try:
                    execute_function('AddEventWithCheck', (nazwa, data, miejsce_id, opis, limit_miejsc, cena, organizer_id))
                    flash("Wydarzenie dodane pomyślnie", 'success')
                except Exception as e:
                    flash(f"Błąd: {str(e)}", 'danger')
        elif action == 'delete':
            event_id = request.form['event_id']
            execute_function('DeleteEvent', (event_id,))
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
                execute_function('UpdateEvent', (event_id, nazwa, data, miejsce_id, opis, limit_miejsc, cena))
                flash("Wydarzenie zaktualizowane pomyślnie", 'success')
    events = fetch_function('GetEvents')
    locations = fetch_function('GetLocations')
    categories = fetch_function('GetCategories')
    return render_template('manage_events.html', events=events, locations=locations, categories=categories)


@app.route('/organizer_dashboard')
def organizer_dashboard():
    if 'user' not in session or session['user']['rola'] != 'organizator':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    return render_template('organizer_dashboard.html')


@app.route('/organizer_events', methods=['GET', 'POST'])
def organizer_events():
    if 'user' not in session or session['user']['rola'] != 'organizator':
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
            organizer_id = session['user']['userid']
            if not (nazwa and data and miejsce_id and opis and limit_miejsc and cena):
                flash("Wszystkie pola są wymagane", 'danger')
            else:
                try:
                    execute_function('AddEventWithCheck', (nazwa, data, miejsce_id, opis, limit_miejsc, cena, organizer_id))
                    flash("Wydarzenie dodane pomyślnie", 'success')
                except Exception as e:
                    flash(f"Błąd: {str(e)}", 'danger')
        elif action == 'delete':
            event_id = request.form['event_id']
            execute_function('DeleteEvent', (event_id,))
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
                execute_function('UpdateEvent', (event_id, nazwa, data, miejsce_id, opis, limit_miejsc, cena))
                flash("Wydarzenie zaktualizowane pomyślnie", 'success')
    events = fetch_function('GetEvents')
    locations = fetch_function('GetLocations')
    categories = fetch_function('GetCategories')
    return render_template('organizer_events.html', events=events, locations=locations, categories=categories)


@app.route('/organizer_bookings')
def organizer_bookings():
    if 'user' not in session or session['user']['rola'] != 'organizator':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    try:
        bookings = fetch_function('GetBookingsByOrganizer', (session['user']['userid'],))
        return render_template('organizer_bookings.html', bookings=bookings)
    except Exception as e:
        print(f"Error: {e}")
        flash(f"Wystąpił błąd podczas pobierania danych. Szczegóły: {e}", 'danger')
        return render_template('organizer_bookings.html', bookings=[])


@app.route('/organizer_profile', methods=['GET', 'POST'])
def organizer_profile():
    if 'user' not in session or session['user']['rola'] != 'organizator':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    user = fetch_function('GetUserById', (session['user']['userid'],))
    user = user[0] if user else {}
    if request.method == 'POST':
        imie = request.form['imie']
        nazwisko = request.form['nazwisko']
        email = request.form['email']
        haslo = request.form['haslo']
        if not (imie and nazwisko and email):
            flash("Wszystkie pola są wymagane", 'danger')
        else:
            execute_function('UpdateUser', (session['user']['userid'], imie, nazwisko, email, haslo))
            flash("Profil zaktualizowany pomyślnie", 'success')
            return redirect(url_for('organizer_dashboard'))
    return render_template('organizer_profile.html', user=user)


@app.route('/book_event', methods=['GET', 'POST'])
def book_event():
    if 'user' not in session or session['user']['rola'] != 'klient':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    events = fetch_function('GetEvents')
    if request.method == 'POST':
        user_id = session['user']['userid']
        event_id = request.form['event_id']
        status = 'aktywny'
        znizka_id = request.form.get('znizka_id')
        if not (user_id and event_id):
            flash("UserID i EventID są wymagane", 'danger')
        else:
            try:
                execute_function('BookTicket', (user_id, event_id, status, znizka_id if znizka_id else None))
                flash("Zarezerwowano pomyślnie", 'success')
            except Exception as e:
                print(f"Error: {e}")
                flash(f"Wystąpił błąd podczas wykonywania operacji. Szczegóły: {e}", 'danger')
    return render_template('book_event.html', events=events)


def calculate_discounted_price(price, birth_date):
    today = datetime.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    discount = Decimal('0.2') if age < 25 or age > 70 else Decimal('0')
    return price * (Decimal('1') - discount)


@app.route('/make_payment', methods=['GET', 'POST'])
def make_payment():
    if 'user' not in session or session['user']['rola'] != 'klient':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        user_id = session['user']['userid']
        ticket_id = request.form['ticket_id']
        try:
            kwota = Decimal(request.form['kwota'])
        except decimal.InvalidOperation:
            flash("Nieprawidłowa wartość kwoty", 'danger')
            return redirect(url_for('make_payment'))
        metoda_platnosci = request.form['metoda_platnosci']

        # Pobierz szczegóły użytkownika korzystając z funkcji GetUserById (zamiast GetUserDetails)
        user_details = fetch_function('GetUserById', (user_id,))
        if not user_details:
            flash("Nie znaleziono szczegółów użytkownika", 'danger')
            return redirect(url_for('make_payment'))

        # Przyjmujemy, że kolumna DataUrodzenia jest zapisana jako lowercase 'dataurodzenia'
        birth_date = user_details[0]['dataurodzenia']
        final_price = calculate_discounted_price(kwota, birth_date)

        try:
            execute_function('MakePayment', (user_id, ticket_id, final_price, metoda_platnosci))
            flash("Płatność zakończona pomyślnie", 'success')
        except Exception as e:
            print(f"Error: {e}")
            flash(f"Wystąpił błąd podczas wykonywania płatności. Szczegóły: {e}", 'danger')
        return redirect(url_for('book_event'))

    user_id = session['user']['userid']
    tickets = fetch_function('GetTicketsByUser', (user_id,))

    user_details = fetch_function('GetUserById', (user_id,))
    if not user_details:
        flash("Nie znaleziono szczegółów użytkownika", 'danger')
        return redirect(url_for('book_event'))
    birth_date = user_details[0]['dataurodzenia']

    for ticket in tickets:
        if ticket['base_price'] is not None:
            try:
                ticket['FinalPrice'] = calculate_discounted_price(Decimal(ticket['base_price']), birth_date)
            except Exception as e:
                print(f"Error calculating discounted price for ticket {ticket['ticketid']}: {e}")
                ticket['FinalPrice'] = ticket['base_price']
        else:
            print(f"Warning: Ticket {ticket['ticketid']} has no price set (base_price is None).")
            ticket['FinalPrice'] = 'Brak ceny'

    return render_template('make_payment.html', tickets=tickets)


@app.route('/filter_events', methods=['GET', 'POST'])
def filter_events():
    if 'user' not in session or session['user']['rola'] != 'klient':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    events = []
    if request.method == 'POST':
        category = request.form['category']
        city = request.form['city']
        country = request.form['country']
        date_from = request.form['date_from']
        date_to = request.form['date_to']
        capacity_min = request.form['capacity_min']
        capacity_max = request.form['capacity_max']
        seat_type = request.form['seat_type']
        price_min = request.form['price_min']
        price_max = request.form['price_max']
        available_only = request.form.get('available_only')
        events = fetch_function('FilterEvents', (category, f"%{city}%", f"%{country}%", date_from, date_to, capacity_min, capacity_max, f"%{seat_type}%", price_min, price_max, available_only))
    categories = fetch_function('GetCategories')
    return render_template('filter_events.html', events=events, categories=categories)


@app.route('/reports')
def reports():
    return render_template('reports.html')


@app.route('/report/events_per_category')
def report_events_per_category():
    results = fetch_function('ReportEventsPerCategory')
    return render_template('report.html', title="Liczba wydarzeń w poszczególnych kategoriach", results=results)


@app.route('/report/average_rating_per_category')
def report_average_rating_per_category():
    results = fetch_function('ReportAverageRatingPerCategory')
    return render_template('report.html', title="Średnia ocena wydarzeń w poszczególnych kategoriach", results=results)


@app.route('/report/top_selling_events')
def report_top_selling_events():
    results = fetch_function('ReportTopSellingEvents')
    return render_template('report.html', title="Najczęściej kupowane bilety w poszczególnych kategoriach", results=results)


@app.route('/report/most_rated_events')
def report_most_rated_events():
    results = fetch_function('ReportMostRatedEvents')
    return render_template('report.html', title="Najczęściej oceniane wydarzenia", results=results)


@app.route('/report/event_revenue')
def report_event_revenue():
    results = fetch_function('ReportEventRevenue')
    return render_template('report.html', title="Suma wpływów z poszczególnych wydarzeń", results=results)


@app.route('/report/revenue_in_period', methods=['GET', 'POST'])
def report_revenue_in_period():
    results = []
    if request.method == 'POST':
        date_from = request.form['date_from']
        date_to = request.form['date_to']
        results = fetch_function('ReportRevenueInPeriod', (date_from, date_to))
    return render_template('report_revenue_in_period.html', title="Suma wpływów z wydarzeń w danym okresie", results=results)


def main():
    app.run(host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
