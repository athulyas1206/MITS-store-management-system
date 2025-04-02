from flask import Flask, render_template, request, redirect, flash, session, url_for
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
from PyPDF2 import PdfReader
from flask_mail import Mail, Message
import random
import re  # Import regex for validation

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'mitsstoremanager@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'avvj xaom hmyc zumk'  # Replace with your email password or app password
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

UPLOAD_FOLDER = 'static/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_user(mut_id, password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE mut_id=? AND password=?', (mut_id, password))
    user = cursor.fetchone()
    conn.close()
    return user

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mut_id = request.form['mut_id']
        password = request.form['password']

        if mut_id == 'admin' and password == 'admin':  # Change to a secure password
            session['mut_id'] = 'admin'
            flash('Admin login successful!', 'success')
            return redirect('/admin_dashboard')

        user = validate_user(mut_id, password)
        if user:
            session['user_id'] = user[0]  # Store user ID in session
            session['mut_id'] = user[1]  # Store MUT ID in session

            return redirect('/home')
        else:
            flash('Invalid MUT ID or Password. Try again.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        mut_id = request.form['mut_id']
        email = request.form['email']
        password = request.form['password']
        
        # Validate MUT ID format
        if not re.match(r'^MUT\d{2}(AD|CS|CE|ME|EE|EC)\d{3}$', mut_id):
            flash('Invalid MUT ID format.','danger')
            return redirect('/register')

        # Validate email domain
        if not email.endswith('@mgits.ac.in'):
            flash('Email must be from the @mgits.ac.in domain.', 'danger')
            return redirect('/register')

        # Check if the email is not the admin email
        if email == 'mitsstoremanager@gmail.com':
            flash('Admin email cannot be used for registration.', 'danger')
            return redirect('/register')

        otp = str(random.randint(100000, 999999))  # Generate a random 6-digit OTP
        session['otp'] = otp  # Store OTP in session for verification
        session['mut_id'] = mut_id  # Store mut_id in session for later use
        session['email'] = email  # Store email in session for later use
        session['password'] = password  # Store password in session for later use

        # Send OTP email
        send_otp(email, otp)

        flash('Registration successful! Please check your email for the OTP.', 'success')
        return redirect('/verify_otp')  # Redirect to OTP verification page

    return render_template('register.html')

def send_otp(to_email, otp):
    subject = "Your OTP for Email Verification"
    body = f"""
    <h1>Email Verification</h1>
    <p>Your OTP is: <strong>{otp}</strong></p>
    <p>Please enter this OTP to verify your email address.</p>
    """

    msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[to_email])
    msg.html = body

    try:
        mail.send(msg)
        print("OTP email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        mut_id = session.get('mut_id')
        email = session.get('email')
        password = session.get('password')  # Retrieve password from session

        if entered_otp == session.get('otp'):
            # OTP is correct, save user to the database
            try:
                conn = sqlite3.connect('users.db', timeout=10)
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (mut_id, email, password) VALUES (?, ?, ?)', 
                               (mut_id, email, password))  # Use password from session
                conn.commit()
                flash('Email verified successfully! You can now log in.', 'success')
                return redirect('/login')
            except sqlite3.IntegrityError:
                flash('MUT ID or Email already exists.', 'danger')
            except sqlite3.OperationalError as e:
                flash('Database error: {}'.format(e), 'danger')
            finally:
                cursor.close()
                conn.close()
        else:
            flash('Invalid OTP. Please try again.', 'danger')
            return redirect('/verify_otp')  # Redirect to OTP verification page

    return render_template('verify_otp.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('mut_id') != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect('/login')

    conn = sqlite3.connect('print_orders.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM print_orders ORDER BY expected_datetime DESC')
    orders = cursor.fetchall()
    cursor.execute("SELECT * FROM print_orders")
    order_history = cursor.fetchall()
    conn.close()

    return render_template('admin.html', orders=orders, order_history=order_history)

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    conn = sqlite3.connect('print_orders.db')
    cursor = conn.cursor()
    cursor.execute("SELECT mut_id, copies, layout, print_type, print_sides, expected_datetime, pdf_filename FROM print_orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()

    if order:
        cursor.execute("""
            INSERT INTO order_history (mut_id, copies, layout, print_type, print_sides, expected_datetime, pdf_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, order)
        conn.commit()
        cursor.execute("DELETE FROM print_orders WHERE id = ?", (order_id,))
        conn.commit()

    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/order_history')
def order_history():
    conn = sqlite3.connect("print_orders.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM order_history ORDER BY deleted_at DESC")
    orders = cursor.fetchall()
    conn.close()
    return render_template("admin.html", orders=orders)

@app.route('/update_status', methods=['POST'])
def update_status():
    order_id = request.form['order_id']
    new_status = request.form['status']

    conn = sqlite3.connect("print_orders.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE print_orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()

@app.route('/upload/<filename>')
def upload(filename):
    return f"File {filename} uploaded successfully!"

@app.route('/home')
def home():
    if 'user_id' in session:
        return render_template('home.html', mut_id=session['mut_id'])
    else:
        
        return redirect('/login')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect('/login')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/stationary')
def stationary():
    return render_template('stationary.html')

@app.route('/print_orders', methods=['GET', 'POST'])
def create_print_orders():
    if request.method == 'POST':
        mut_id = session.get('mut_id')
        copies = int(request.form['copies'])
        layout = request.form['layout']
        print_type = request.form['print_type']
        print_sides = request.form['print_sides']
        expected_datetime = request.form['expected_datetime']
        pdf = request.files['pdf_upload']

        expected_dt = datetime.strptime(expected_datetime, '%Y-%m-%dT%H:%M')
        if expected_dt <= datetime.now():
            flash('Expected date and time must be in the future.', 'danger')
            return redirect('/print_orders')

        pdf_filename = f"{mut_id}_{pdf.filename}"
        pdf_path = os.path.join(UPLOAD_FOLDER, pdf_filename)
        pdf.save(pdf_path)

        pdf_reader = PdfReader(pdf_path)
        num_pages = len(pdf_reader.pages)

        cost_per_page = 2 if print_type == 'black_white' else 5
        total_cost = num_pages * cost_per_page * copies

        # Store order details in session
        session['order_details'] = {
            'mut_id': mut_id,
            'copies': copies,
            'layout': layout,
            'print_type': print_type,
            'print_sides': print_sides,
            'expected_datetime': expected_datetime,
            'pdf_filename': pdf_filename,
            'num_pages': num_pages,
            'total_cost': total_cost
        }

        return redirect('/order_summary')  # Redirect to order summary page

    return render_template('print_orders.html')

@app.route('/order_summary', methods=['GET', 'POST'])
def order_summary():
    order_details = session.get('order_details')
    
    if not order_details:
        flash('No order details found. Please create an order first.', 'danger')
        return redirect('/print_orders')

    return render_template('order_summary.html', **order_details)

@app.route('/confirm_order', methods=['POST'])
def confirm_order():
    order_details = session.get('order_details')
    
    if not order_details:
        flash('No order details found. Please create an order first.', 'danger')
        return redirect('/print_orders')

    # Save the order to the database
    conn = sqlite3.connect('print_orders.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO print_orders (mut_id, copies, layout, print_type, print_sides, expected_datetime, pdf_filename, num_pages, total_cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (order_details['mut_id'], order_details['copies'], order_details['layout'], 
          order_details['print_type'], order_details['print_sides'], order_details['expected_datetime'], 
          order_details['pdf_filename'], order_details['num_pages'], order_details['total_cost']))
    conn.commit()
    conn.close()

    # Fetch user email from the database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT email FROM users WHERE mut_id=?', (order_details['mut_id'],))
    user = cursor.fetchone()
    conn.close()

    if user:
        user_email = user[0]
        # Send order summary email
        send_order_summary_email(user_email, order_details['num_pages'], order_details['copies'], order_details['total_cost'])

    # Clear the order details from the session
    session.pop('order_details', None)
    flash('Order confirmed! A summary has been sent to your email.', 'success')
    return redirect('/home')


def send_order_summary_email(to_email, num_pages, copies, total_cost):
    subject = "Your Order Summary"
    body = f"""
    <h1>Your order is successfully placed!</h1>
    <h1>Order Summary</h1>
    <p>Thank you for your order!</p>
    <p>Number of Pages: {num_pages}</p>
    <p>Copies: {copies}</p>
    <p>Total Cost: Rs {total_cost}</p>
    <p>We appreciate your business!</p>
    """

    msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[to_email])
    msg.html = body

    try:
        mail.send(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")




@app.route('/pay_on_google_pay', methods=['POST'])
def pay_on_google_pay():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect('/login')

    num_pages = request.form['num_pages']
    copies = request.form['copies']
    total_cost = request.form['total_cost']
    mut_id = session.get('mut_id')

    # Fetch user email from the database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT email FROM users WHERE mut_id=?', (mut_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        user_email = user[0]
        send_order_summary_email(user_email, num_pages, copies, total_cost)

    flash('Payment initiated! A summary has been sent to your email.', 'success')
    return redirect('/home')

@app.route('/cancel_order')
def cancel_order():
    # Set a flash message indicating the order has been canceled
    flash('Your order is cancelled.', 'info')
    return redirect(url_for('home'))



if __name__ == '__main__':
    app.run(debug=True)