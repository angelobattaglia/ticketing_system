# Note: it is important to add "render_template" to the imports
from flask import Flask, render_template
from flask import Flask, render_template, request
from flask import redirect, url_for, flash, abort

# Flask-Login is a Flask extension that provides a framework for handling user authentication
import flask_login
from flask_login import LoginManager
from flask_login import login_required
# Logs a user in. We should pass the actual user object to this method:
# returns True if the log in attempt succeeds, and False if it fails
from flask_login import login_user

# Security and Forms for the login
import werkzeug.security as ws
# from forms import LoginForm

# Import the datetime library to handle the pubblication date of the raccolte
import datetime

## Import the dao modules and the models module
import models
import utenti_dao
import trains_dao
import bookings_dao

## Here I call these functions for the creation of the DB tables at startup time
from table_creation import create_table_users, create_table_trains, create_table_bookings, create_table_train_capacity
create_table_users()
create_table_trains()
create_table_bookings()
create_table_train_capacity()

## Calling the method to populate the DB
from populate import populate#, populate_solutions
populate()
# populate_solutions()

# create the application
app = Flask(__name__)

app.config['SECRET_KEY'] = 'gematria'


# This is for login_manager 
login_manager = LoginManager()
login_manager.init_app(app)

@app.route('/')
def home():
    return render_template('home.html', title='Home', active_page='home', search=False)

#########################################################
#########################################################
#########################################################
########## Here I make the profile page of an user ######
#########################################################
#########################################################
#########################################################
#########################################################

# Per convertire il tempo nella visualizzazione
def minutes_to_time(minutes):
    minutes = int(minutes)  # Convert string to integer
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02}:{mins:02}"

# Profile page for each user with dynamic routing
@app.route('/profile/<int:user_id>', methods=['GET'])
@flask_login.login_required
def profile(user_id):
    # Find the user by its ID
    user = None
    for u in utenti_dao.get_users():
        if u[0] == user_id:
            user = u
            break

    # Controllo che il treno sia stato trovato, in caso negativo faccio un redirect alla home
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('home'))

    # Faccio il "retrieve" di tutti i bookings che appartengono al determinato utente
    bookings = bookings_dao.get_bookings_for_user(user_id)

    formatted_bookings = []
    for booking in bookings:
        booking = list(booking)
        booking[17] = minutes_to_time(booking[17])  # departure_time corrisponde all'indice 17 nella struttura dati
        formatted_bookings.append(booking)

    # Passo il treno alla bagina booking_form.html
    return render_template('profile.html', user=u, bookings=formatted_bookings, active_page='profile')

#########################################################
#########################################################
#########################################################
###### Here I make the method to delete a booking #######
#########################################################
#########################################################
#########################################################
#########################################################

@app.route('/delete_booking/<int:booking_id>', methods=['POST'])
@flask_login.login_required
def delete_booking(booking_id):
    # Retrieve the booking to ensure it belongs to the current user
    booking = bookings_dao.get_booking_by_id(booking_id)
    
    if booking and booking[1] == flask_login.current_user.id:
        bookings_dao.delete_booking(booking_id)
        flash('Booking annulled successfully.', 'success')
    else:
        flash('Booking not found or you do not have permission to delete it.', 'danger')
    
    return redirect(url_for('profile', user_id=flask_login.current_user.id))

@app.route('/modify_booking', methods=['POST'])
@flask_login.login_required
def modify_booking():
    booking_id = request.form.get('booking_id')
    # # Retrieve the booking to ensure it belongs to the current user
    booking = bookings_dao.get_booking_by_id(booking_id)
    
    # if not booking or booking[0] != flask_login.current_user.id:
    #     flash('Booking not found or you do not have permission to modify it.', 'danger')
    #     return redirect(url_for('profile', user_id=flask_login.current_user.id))
    
    # # Check if the modification is within the allowed timeframe
    # departure_time = datetime.datetime.fromtimestamp(float(booking[17]))  # Assuming 17 is the index for departure_time
    # current_time = datetime.datetime.now()
    # if (departure_time - current_time).total_seconds() < 120:
    #     flash('Modification not allowed within 2 minutes of departure.', 'danger')
    #     return redirect(url_for('profile', user_id=flask_login.current_user.id))

    # Get new train details from the form
    new_train_id = request.form.get('train_id')
    
    # Validate the new train details
    if not new_train_id:
        flash('Invalid train selection.', 'danger')
        return redirect(url_for('profile', user_id=flask_login.current_user.id))

    # Perform the modification
    success = bookings_dao.modify_booking(booking_id, new_train_id)
    
    if success:
        flash('Booking modified successfully.', 'success')
    else:
        flash('Failed to modify booking.', 'danger')
    
    return redirect(url_for('profile', user_id=flask_login.current_user.id))

#########################################################
#########################################################
#########################################################
########## I make the booking and search system #########
#########################################################
#########################################################
#########################################################
#########################################################

# mostra i posti disponibili, se il treno è pieno non si può prenotare
@app.route('/search_trains', methods=['POST'])
def search_trains():
    departure_city = request.form['departure_city']
    arrival_city = request.form['arrival_city']
    departure_date = request.form['departure_date']

    # Validate the form inputs
    if departure_city == arrival_city:
        flash('Departure city and arrival city cannot be the same.', 'danger')
        return redirect(url_for('home'))
    if datetime.datetime.strptime(departure_date, '%Y-%m-%d') < datetime.datetime.now():
        flash('Departure date cannot be in the past.', 'danger')
        return redirect(url_for('home'))

    # Search for trains
    results = trains_dao.search_trains(departure_city, arrival_city, departure_date)
    if not results:
        flash('No trains available for the selected route and date.', 'info')

    formatted_results = []
    for train in results:
        train = list(train)
        train_departure_time_index = 5
        train[train_departure_time_index] = minutes_to_time(train[train_departure_time_index])
        train_arrival_time_index = 6
        train[train_arrival_time_index] = minutes_to_time(train[train_arrival_time_index])
        formatted_results.append(train)

    min_date = datetime.datetime.now().strftime('%Y-%m-%d')
    return render_template('home.html', title='Search Results', departure_city=departure_city, arrival_city=arrival_city, departure_date=departure_date, min_date=min_date, trains=formatted_results, search=True)

# Booking form with dynamic routing
@app.route('/booking_form/<int:train_id>', methods=['GET'])
@flask_login.login_required
def booking_form(train_id):
    # Find the train by its ID
    train = None
    for t in trains_dao.get_trains():
        if t[0] == train_id:
            train = t
            break

    # Controllo che il treno sia stato trovato, in caso negativo faccio un redirect alla home
    if not train:
        flash('Train not found', 'danger')
        return redirect(url_for('home'))

    # is_high_speed è un dato booleano, che deriva proprio dal controllo logico che viene fatto a sinistra
    is_high_speed = train[8] == "High-speed"

    # Passo il treno alla bagina booking_form.html
    return render_template('booking_form.html', train_id=train_id, is_high_speed=is_high_speed)

# Edit Booking form with dynamic routing
@app.route('/edit_booking/<int:booking_id>', methods=['GET'])
@flask_login.login_required
def edit_booking(booking_id):
    booking = bookings_dao.get_booking_by_id(booking_id)
    trains = trains_dao.get_trains()
    is_high_speed = booking[19] == "High-speed"
    return render_template('booking_edit.html', trains=trains, booking=booking, is_high_speed=is_high_speed)

@app.route('/book_ticket', methods=['POST'])
def book_ticket():
    # Prendo il tempo corrente
    booking_time = datetime.datetime.now()

    train_id = request.form['train_id']
    user_id = flask_login.current_user.id
    name = request.form['name']
    surname = request.form['surname']
    address = request.form['address']
    city = request.form['city']
    credit_card = request.form['credit_card']
    expire_date_card = request.form['expire_date_card']
    number_of_tickets = int(request.form['number_of_tickets'])
    seat = request.form.get('seat')  # Seat is optional

    train = trains_dao.get_train_by_id(train_id)
    # train[1] # Questo dovrebbe essere il codice alfanumerico :pray:
    # Faccio un controllo per essere sicuro che questo treno effettivamente esista
    if not train:
        flash('Train ID not found', 'error')
        return redirect(url_for('home'))

    # Here you would add the logic to handle the booking, such as saving the booking to a database
    bookings_dao.insert_booking(user_id, train_id, train[1], booking_time, name, surname, address, city, credit_card, expire_date_card, number_of_tickets, seat)

    flash(f'Ticket for train {train_id} booked successfully!', 'success')
    return redirect(url_for('home'))

#########################################################
#########################################################
#########################################################
#######First the login and the sign-up page##############
#########################################################
#########################################################
#########################################################
#########################################################

# Define the signup page
@app.route('/signup')
def signup():
    return render_template('signup.html', active_page='signup')

@app.route('/signup', methods=['GET', 'POST'])
def signup_function():

    # I take from the form the input datas and import them locally as a dictionary
    nuovo_utente_form = request.form.to_dict()

    # I try to retrieve the unique email of the nuovo_utente_form from the db ..
    user_in_db = utenti_dao.get_user_by_email(nuovo_utente_form.get('email'))

    # ... and I check weather it has already been registered ..
    if user_in_db:
        flash('There\'s already a user with these credentials', 'danger')
        return redirect(url_for('signup'))
    # .. and if it hasn't been registered ..
    else:
        # I generate an hash for the password that has been inserted by the form input
        nuovo_utente_form['password'] = ws.generate_password_hash(nuovo_utente_form.get('password'))

        # I add the user to the db using the method "add_user" from the utenti_dao.py
        success = utenti_dao.add_user(nuovo_utente_form)

        if success:
            flash('Utente creato correttamente', 'success')
            return redirect(url_for('home'))
        else:
            flash('Errore nella creazione del utente: riprova!', 'danger')
            return redirect(url_for('signup'))

@login_manager.user_loader
def load_user(user_id):
    db_user = utenti_dao.get_user_by_id(user_id)
    if db_user is not None:
        user = models.User(id=db_user['id'], 
                           email=db_user['email'],
                           password=db_user['password'])
    else:
        user = None
    return user

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html', active_page='login')

@app.route('/login', methods=['POST'])
def login_post():

    # Retrieving the informations from the form @ /login
    utente_form = request.form.to_dict()
    # Using the "get_user_by_nickname" method from utenti.dao, which
    # retrieves the user from the database with the given nickname passed
    # from the form in /login
    utente_db = utenti_dao.get_user_by_email(utente_form['email'])

    # If there's no utente_db in the database (meaning the user just doesn't exist into the db)
    # or if the password given as input in the form /login isn't equal to the one in the database
    if not utente_db or not ws.check_password_hash(utente_db['password'], utente_form['password']):
        flash('Credenziali non valide, riprova', 'danger')
        return redirect(url_for('home'))
    else:
    # if, instead, it exists, we create a new user instance using the "User model" defined in models.py
        # Create a new user instance called "new"
        new = models.User(id=utente_db['id'], 
                          email=utente_db['email'],
                          password=utente_db['password'])
        # We log in said user called "new"
        flask_login.login_user(new, True)
        flash('Bentornato ' + utente_db['email'] + '!', 'success')
        return redirect(url_for('home'))

# Log out route
@app.route("/logout")
@login_required
def logout():
    flask_login.logout_user()
    return redirect(url_for('home'))

@app.route('/about')
def about():
    return render_template('about.html', title='About Us', active_page='about')
