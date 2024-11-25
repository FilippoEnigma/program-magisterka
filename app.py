import decimal
from datetime import datetime
import configparser
import mysql.connector
from mysql.connector import Error
from flask import Flask, render_template, request, redirect, url_for, session, flash, current_app
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

# Dodajemy current_app do kontekstu szablonu
@app.context_processor
def inject_current_app():
    return dict(current_app=current_app)

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
def organizer_profile():
    if 'user' not in session or session['user']['Rola'] != 'organizator':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    user = get_user_by_id(session['user']['UserID'])
    if request.method == 'POST':
        imie = request.form['imie']
        nazwisko = request.form['nazwisko']
        email = request.form['email']
        haslo = request.form['haslo']
        if not (imie and nazwisko and email):
            flash("Wszystkie pola są wymagane", 'danger')
        else:
            update_user(session['user']['UserID'], imie, nazwisko, email, haslo)
            flash("Profil zaktualizowany pomyślnie", 'success')
            return redirect(url_for('organizer_dashboard'))
    return render_template('organizer_profile.html', user=user)

def get_user_details(user_id):
    query = "SELECT UserID, Imie, Nazwisko, Email, DataUrodzenia FROM users WHERE UserID = %s"
    result = fetch_query(query, (user_id,))
    return result[0] if result else None

def get_event_price(event_id):
    query = "SELECT Cena FROM events WHERE EventID = %s"
    result = fetch_query(query, (event_id,))
    return result[0]['Cena'] if result else None

def insert_ticket(user_id, event_id, status, znizka_id, final_price):
    query = """INSERT INTO tickets (UserID, EventID, DataZakupu, Status, ZnizkaID, FinalPrice)
               VALUES (%s, %s, NOW(), %s, %s, %s)"""
    return execute_query(query, (user_id, event_id, status, znizka_id, final_price))

@app.route('/book_event', methods=['GET', 'POST'])
def book_event():
    if 'user' not in session or session['user']['Rola'] != 'klient':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))
    events = get_events()
    if request.method == 'POST':
        user_id = session['user']['UserID']
        event_id = request.form['event_id']
        status = 'aktywny'
        znizka_id = request.form.get('znizka_id')
        if not (user_id and event_id):
            flash("UserID i EventID są wymagane", 'danger')
        else:
            try:
                user_details = get_user_details(user_id)
                if not user_details:
                    flash("Nie znaleziono danych użytkownika.", 'danger')
                    return redirect(url_for('book_event'))
                birth_date = user_details['DataUrodzenia']
                base_price = get_event_price(event_id)
                if base_price is None:
                    flash("Nie znaleziono ceny wydarzenia.", 'danger')
                    return redirect(url_for('book_event'))
                final_price = calculate_discounted_price(Decimal(base_price), birth_date)
                insert_ticket(user_id, event_id, status, znizka_id, final_price)
                flash("Zarezerwowano pomyślnie", 'success')
            except Exception as e:
                print(f"Błąd: {e}")
                flash(f"Wystąpił błąd podczas wykonywania operacji. Szczegóły: {e}", 'danger')
    return render_template('book_event.html', events=events)

def calculate_discounted_price(price, birth_date):
    today = datetime.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    discount = Decimal('0.2') if age < 25 or age > 70 else Decimal('0')
    return price * (Decimal('1') - discount)

def get_ticket_final_price(ticket_id):
    query = "SELECT FinalPrice FROM tickets WHERE TicketID = %s"
    result = fetch_query(query, (ticket_id,))
    return result[0]['FinalPrice'] if result else None

def make_payment(user_id, ticket_id, kwota, metoda_platnosci):
    query = """INSERT INTO payments (UserID, TicketID, Kwota, DataPlatnosci, MetodaPlatnosci)
               VALUES (%s, %s, %s, NOW(), %s)"""
    return execute_query(query, (user_id, ticket_id, kwota, metoda_platnosci))

def update_ticket_status(ticket_id, status):
    query = "UPDATE tickets SET Status = %s WHERE TicketID = %s"
    return execute_query(query, (status, ticket_id))

def get_tickets_by_user(user_id):
    query = """SELECT T.TicketID, E.NazwaWydarzenia, E.Data, E.Cena, T.FinalPrice
               FROM tickets T
               JOIN events E ON T.EventID = E.EventID
               WHERE T.UserID = %s"""
    return fetch_query(query, (user_id,))

@app.route('/make_payment', methods=['GET', 'POST'])
def make_payment():
    if 'user' not in session or session['user']['Rola'] != 'klient':
        flash("Brak dostępu", 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        user_id = session['user']['UserID']
        ticket_id = request.form['ticket_id']
        metoda_platnosci = request.form['metoda_platnosci']

        final_price = get_ticket_final_price(ticket_id)
        if final_price is None:
            flash("Nie znaleziono ceny biletu.", 'danger')
            return redirect(url_for('make_payment'))

        try:
            make_payment(user_id, ticket_id, final_price, metoda_platnosci)
            update_ticket_status(ticket_id, 'zakupiony')
            flash("Płatność zakończona pomyślnie", 'success')
        except Exception as e:
            print(f"Błąd: {e}")
            flash(f"Wystąpił błąd podczas wykonywania płatności. Szczegóły: {e}", 'danger')
        return redirect(url_for('book_event'))

    user_id = session['user']['UserID']
    tickets = get_tickets_by_user(user_id)

    return render_template('make_payment.html', tickets=tickets)

def filter_events(category, city, country, date_from, date_to, capacity_min, capacity_max, seat_type, price_min, price_max, available_only):
    query = """
    SELECT E.NazwaWydarzenia, E.Data, L.Miasto, L.Kraj, L.Pojemnosc, L.RodzajMiejsc, E.Opis, E.Cena, 
           E.LimitMiejsc - IFNULL(SUM(CASE WHEN T.Status = 'aktywny' THEN 1 ELSE 0 END), 0) AS DostepneMiejsca
    FROM events E
    JOIN eventcategoryassignment ECA ON E.EventID = ECA.EventID
    JOIN eventcategories EC ON ECA.CategoryID = EC.CategoryID
    JOIN location L ON E.MiejsceID = L.LocationID
    LEFT JOIN tickets T ON E.EventID = T.EventID
    WHERE EC.NazwaKategorii = %s AND L.Miasto LIKE %s AND L.Kraj LIKE %s
          AND E.Data BETWEEN %s AND %s AND L.Pojemnosc BETWEEN %s AND %s
          AND L.RodzajMiejsc LIKE %s AND E.Cena BETWEEN %s AND %s
    GROUP BY E.EventID
    HAVING (DostepneMiejsca > 0 OR %s = 0);
    """
    return fetch_query(query, (category, city, country, date_from, date_to, capacity_min, capacity_max, seat_type, price_min, price_max, available_only))

@app.route('/filter_events', methods=['GET', 'POST'])
def filter_events_route():
    if 'user' not in session or session['user']['Rola'] != 'klient':
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
        available_only = request.form.get('available_only', '0')
        events = filter_events(category, f"%{city}%", f"%{country}%", date_from, date_to, capacity_min, capacity_max, f"%{seat_type}%", price_min, price_max, available_only)
    categories = get_categories()
    return render_template('filter_events.html', events=events, categories=categories)

@app.route('/reports')
def reports():
    return render_template('reports.html')

def report_events_per_category():
    query = """
    SELECT EC.NazwaKategorii, COUNT(*) AS LiczbaWydarzen
    FROM eventcategoryassignment ECA
    JOIN eventcategories EC ON ECA.CategoryID = EC.CategoryID
    GROUP BY EC.NazwaKategorii;
    """
    return fetch_query(query)

@app.route('/report/events_per_category')
def report_events_per_category_route():
    results = report_events_per_category()
    return render_template('report.html', title="Liczba wydarzeń w poszczególnych kategoriach", results=results)

def report_average_rating_per_category():
    query = """
    SELECT EC.NazwaKategorii, AVG(ER.Ocena) AS SredniaOcena
    FROM eventcategoryassignment ECA
    JOIN eventcategories EC ON ECA.CategoryID = EC.CategoryID
    JOIN events E ON ECA.EventID = E.EventID
    LEFT JOIN eventratings ER ON E.EventID = ER.EventID
    GROUP BY EC.NazwaKategorii;
    """
    return fetch_query(query)

@app.route('/report/average_rating_per_category')
def report_average_rating_per_category_route():
    results = report_average_rating_per_category()
    return render_template('report.html', title="Średnia ocena wydarzeń w poszczególnych kategoriach", results=results)

def report_top_selling_events():
    query = """
    SELECT EC.NazwaKategorii, E.NazwaWydarzenia, COUNT(*) AS LiczbaBiletow
    FROM eventcategoryassignment ECA
    JOIN eventcategories EC ON ECA.CategoryID = EC.CategoryID
    JOIN events E ON ECA.EventID = E.EventID
    JOIN tickets T ON E.EventID = T.EventID
    GROUP BY EC.NazwaKategorii, E.NazwaWydarzenia
    ORDER BY LiczbaBiletow DESC;
    """
    return fetch_query(query)

@app.route('/report/top_selling_events')
def report_top_selling_events_route():
    results = report_top_selling_events()
    return render_template('report.html', title="Najczęściej kupowane bilety w poszczególnych kategoriach", results=results)

def report_most_rated_events():
    query = """
    SELECT E.NazwaWydarzenia, COUNT(*) AS LiczbaOcen
    FROM events E
    JOIN eventratings ER ON E.EventID = ER.EventID
    GROUP BY E.NazwaWydarzenia
    ORDER BY LiczbaOcen DESC;
    """
    return fetch_query(query)

@app.route('/report/most_rated_events')
def report_most_rated_events_route():
    results = report_most_rated_events()
    return render_template('report.html', title="Najczęściej oceniane wydarzenia", results=results)

def report_event_revenue():
    query = """
    SELECT E.NazwaWydarzenia, SUM(P.Kwota) AS SumaWplywow
    FROM events E
    JOIN tickets T ON E.EventID = T.EventID
    JOIN payments P ON T.TicketID = P.TicketID
    GROUP BY E.NazwaWydarzenia
    ORDER BY SumaWplywow DESC;
    """
    return fetch_query(query)

@app.route('/report/event_revenue')
def report_event_revenue_route():
    results = report_event_revenue()
    return render_template('report.html', title="Suma wpływów z poszczególnych wydarzeń", results=results)

def report_revenue_in_period(date_from, date_to):
    query = """
    SELECT SUM(P.Kwota) AS SumaWplywow
    FROM payments P
    WHERE P.DataPlatnosci BETWEEN %s AND %s;
    """
    return fetch_query(query, (date_from, date_to))

@app.route('/report/revenue_in_period', methods=['GET', 'POST'])
def report_revenue_in_period_route():
    results = []
    if request.method == 'POST':
        date_from = request.form['date_from']
        date_to = request.form['date_to']
        results = report_revenue_in_period(date_from, date_to)
    return render_template('report_revenue_in_period.html', title="Suma wpływów z wydarzeń w danym okresie", results=results)

def main():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
