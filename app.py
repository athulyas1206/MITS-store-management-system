from flask import Flask, render_template, request, redirect, flash, session, url_for
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
from PyPDF2 import PdfReader
from flask_mail import Mail, Message

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
            flash('Login successful!', 'success')
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

        try:
            conn = sqlite3.connect('users.db', timeout=10)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (mut_id, email, password) VALUES (?, ?, ?)', (mut_id, email, password))
            conn.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash('MUT ID or Email already exists.', 'danger')
        except sqlite3.OperationalError as e:
            flash('Database error: {}'.format(e), 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

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
        flash('Please log in first.', 'warning')
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

        conn = sqlite3.connect('print_orders.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO print_orders (mut_id, copies, layout, print_type, print_sides, expected_datetime, pdf_filename, num_pages, total_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (mut_id, copies, layout, print_type, print_sides, expected_datetime, pdf_filename, num_pages, total_cost))
        conn.commit()
        conn.close()

        # Fetch user email from the database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM users WHERE mut_id=?', (mut_id,))
        user = cursor.fetchone()
        conn.close()

        if user:
            user_email = user[0]
            #send_order_summary_email(user_email, num_pages, copies, total_cost)

        flash('Order saved successfully! Proceed to payment.', 'success')
        return redirect('/order_summary')

    return render_template('print_orders.html')

@app.route('/order_summary')
def order_summary():
    mut_id = session.get('mut_id')
    conn = sqlite3.connect('print_orders.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT num_pages, copies, total_cost 
        FROM print_orders 
        WHERE mut_id=? 
        ORDER BY id DESC LIMIT 1
    ''', (mut_id,))
    order = cursor.fetchone()
    conn.close()

    if order:
        num_pages, copies, total_cost = order
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM users WHERE mut_id=?', (mut_id,))
        user = cursor.fetchone()
        conn.close()

        if user:
            user_email = user[0]
            send_order_summary_email(user_email, num_pages, copies, total_cost)

        return render_template('order_summary.html', num_pages=num_pages, copies=copies, total_cost=total_cost)
    else:
        flash('No order found.', 'danger')
        return redirect('/home')

def send_order_summary_email(to_email, num_pages, copies, total_cost):
    subject = "Your Order Summary"
    body = f"""
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

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect('/login')

    user_id = session['user_id']
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        if 'profile_photo' in request.files:
            profile_photo = request.files['profile_photo']
            if profile_photo and allowed_file(profile_photo.filename):
                filename = secure_filename(profile_photo.filename)
                profile_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                profile_photo.save(profile_photo_path)

                cursor.execute('UPDATE users SET profile_photo=? WHERE id=?', (filename, user_id))
                conn.commit()

        new_password = request.form.get('new_password')
        if new_password:
            cursor.execute('UPDATE users SET password=? WHERE id=?', (new_password, user_id))
            conn.commit()
            flash('Password updated successfully!', 'success')

    cursor.execute('SELECT mut_id, email, password, profile_photo FROM users WHERE id=?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        mut_id, email, password, profile_photo = user
        return render_template('profile.html', mut_id=mut_id, email=email, password=password, profile_photo=profile_photo)
    else:
        flash('User  not found.', 'danger')
        return redirect('/home')

@app.route('/upload_profile_photo', methods=['POST'])
def upload_profile_photo():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect('/login')

    if 'profile_photo' not in request.files:
        flash('No file part', 'danger')
        return redirect('/profile')

    file = request.files['profile_photo']

    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect('/profile')

    if file and allowed_file(file.filename):
        filename = secure_filename(f"{session['mut_id']}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET profile_photo=? WHERE mut_id=?", (filename, session['mut_id']))
        conn.commit()
        conn.close()

        session['profile_photo'] = filename

        flash('Profile photo updated successfully!', 'success')
        return redirect('/profile')
    else:
        flash('Invalid file format. Please upload PNG, JPG, or JPEG.', 'danger')
        return redirect('/profile')

if __name__ == '__main__':
    app.run(debug=True)