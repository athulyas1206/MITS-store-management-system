from flask import Flask, render_template, request, redirect, flash, session,url_for,jsonify,flash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
from PyPDF2 import PdfReader


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
    # Redirect to login page as the landing page
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

@app.route('/admin_dashboard')
def admin_dashboard():
    # Check if the user is admin
    if session.get('mut_id') != 'admin':
        flash('Unauthorized access.', 'danger')
        return redirect('/login')

    # Fetch all print orders from the database
    conn = sqlite3.connect('print_orders.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM print_orders ORDER BY expected_datetime DESC')
    orders = cursor.fetchall()
    
    # Fetch completed orders (order history)
    cursor.execute("SELECT * FROM print_orders")
    order_history = cursor.fetchall()
    conn.close()

    return render_template('admin.html', orders=orders ,order_history=order_history)



@app.route('/update_status', methods=['POST'])
def update_status():
        order_id = request.form['order_id']
        new_status = request.form['status']

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE print_orders SET status = ? WHERE id = ?", (new_status, order_id))
        conn.commit()
        conn.close()

        
@app.route('/upload/<filename>')
def upload(filename):
    return f"File {filename} uploaded successfully!"

def register():
    if request.method == 'POST':
        mut_id = request.form['mut_id']
        email = request.form['email']
        password = request.form['password']

        try:
            # Connect with timeout to wait for the lock to release
            conn = sqlite3.connect('users.db', timeout=10)
            cursor = conn.cursor()
            
            # Insert new user
            cursor.execute('INSERT INTO users (mut_id, email, password) VALUES (?, ?, ?)', (mut_id, email, password))
            
            # Commit the transaction
            conn.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash('MUT ID or Email already exists.', 'danger')
        
        except sqlite3.OperationalError as e:
            flash('Database error: {}'.format(e), 'danger')
        
        finally:
            # Close cursor and connection properly
            cursor.close()
            conn.close()

    return render_template('register.html')



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
        # Get form data
        mut_id = session.get('mut_id')
        copies = int(request.form['copies'])
        layout = request.form['layout']
        print_type = request.form['print_type']
        print_sides = request.form['print_sides']
        expected_datetime = request.form['expected_datetime']
        pdf = request.files['pdf_upload']

        # Check if the expected datetime is in the future
        expected_dt = datetime.strptime(expected_datetime, '%Y-%m-%dT%H:%M')
        if expected_dt <= datetime.now():
            flash('Expected date and time must be in the future.', 'danger')
            return redirect('/print_orders')

        # Save the uploaded PDF file
        pdf_filename = f"{mut_id}_{pdf.filename}"
        pdf_path = os.path.join(UPLOAD_FOLDER, pdf_filename)
        pdf.save(pdf_path)

        # Extract the number of pages using PyPDF2
        pdf_reader = PdfReader(pdf_path)
        num_pages = len(pdf_reader.pages)

        # Calculate total cost
        cost_per_page = 2 if print_type == 'black_white' else 5
        total_cost = num_pages * cost_per_page * copies

        # Insert order details into database
        conn = sqlite3.connect('print_orders.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO print_orders (mut_id, copies, layout, print_type, print_sides, expected_datetime, pdf_filename, num_pages, total_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (mut_id, copies, layout, print_type, print_sides, expected_datetime, pdf_filename, num_pages, total_cost))
        conn.commit()
        conn.close()

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
        return render_template('order_summary.html', num_pages=num_pages, copies=copies, total_cost=total_cost)
    else:
        flash('No order found.', 'danger')
        return redirect('/print_orders')

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    conn = sqlite3.connect('print_orders.db')
    cursor = conn.cursor()

    # ✅ Retrieve the order details before deleting
    cursor.execute("SELECT mut_id, copies, layout, print_type, print_sides, expected_datetime FROM print_orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()

    if order:
        # ✅ Print query for debugging
        print("Order found:", order)

        # ✅ Insert into order_history (columns must match exactly)
        cursor.execute("""
            INSERT INTO order_history (mut_id, copies, layout, print_type, print_sides, expected_datetime)
            VALUES (?, ?, ?, ?, ?, ?)
        """, order)

        conn.commit()  # Commit after inserting into history

        # ✅ Now delete only from print_orders
        cursor.execute("DELETE FROM print_orders WHERE id = ?", (order_id,))
        conn.commit()  # Commit the deletion

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





@app.route('/orders')
def orders():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect('/login')

    conn = sqlite3.connect('print_orders.db')
    cursor = conn.cursor()

    # Fetch Print Orders
    cursor.execute("SELECT id, expected_datetime, status FROM print_orders WHERE mut_id=?", (session['mut_id'],))
    print_orders = cursor.fetchall()

    # Fetch Stationary Orders (to be implemented later)
    cursor.execute("SELECT id, expected_datetime, status FROM stationary_orders WHERE mut_id=?", (session['mut_id'],))
    stationary_orders = cursor.fetchall()

    conn.close()

    return render_template('orders.html', print_orders=print_orders, stationary_orders=stationary_orders)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect('/login')

    user_id = session['user_id']
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        # Handle profile photo upload
        if 'profile_photo' in request.files:
            profile_photo = request.files['profile_photo']
            if profile_photo and allowed_file(profile_photo.filename):
                filename = secure_filename(profile_photo.filename)
                profile_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                profile_photo.save(profile_photo_path)

                # Update the user's profile photo in the database
                cursor.execute('UPDATE users SET profile_photo=? WHERE id=?', (filename, user_id))
                conn.commit()

        # Handle password update
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

        # Save the filename to the database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET profile_photo=? WHERE mut_id=?", (filename, session['mut_id']))
        conn.commit()
        conn.close()

        # Update session variable
        session['profile_photo'] = filename

        flash('Profile photo updated successfully!', 'success')
        return redirect('/profile')
    else:
        flash('Invalid file format. Please upload PNG, JPG, or JPEG.', 'danger')
        return redirect('/profile')


if __name__ == '__main__':
    app.run(debug=True)