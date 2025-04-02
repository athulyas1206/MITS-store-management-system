from flask import Flask, render_template, request, redirect, flash, session,url_for,jsonify
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
from PyPDF2 import PdfReader


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#UPLOAD_FOLDER = 'static/profile_pics'
#ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#os.makedirs('static/profile_pics', exist_ok=True)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        print("Form submitted")
        mut_id = request.form['mut_id']
        email = request.form['email']
        password = request.form['password']

        print(f"MUT ID: {mut_id}, Email: {email}, Password: {password}")

        # Set a default photo if none is uploaded
        photo_filename = 'default_profile.png'  # Default profile picture

        #if photo and allowed_file(photo.filename):
        #    # Save the uploaded photo
        #    photo_filename = f"{mut_id}.png"  # You can customize the filename as needed
        #    photo.save(os.path.join('static/profile_pics', photo_filename))  # Save to static folder

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
            print('MUT ID or Email already exists.')
        
        except sqlite3.OperationalError as e:
            flash('Database error: {}'.format(e), 'danger')
            print(f"Database error: {e}")

        finally:
            # Close cursor and connection properly
            cursor.close()
            conn.close()

    return render_template('register.html')

@app.route('/home')
def home():
    # Assuming you have user ID stored in session after login
    user_id = session.get('user_id')  # Get the user ID from the session

    if user_id is None:
        flash('You need to log in first.', 'warning')
        return redirect('/login')

    # Connect to the database to fetch user information
    conn = sqlite3.connect("users.db")  # Use your actual database
    cursor = conn.cursor()
    
    # Fetch the user's MUT ID and Email based on the user ID
    cursor.execute("SELECT mut_id, email FROM users WHERE id = ?", (user_id,))
    user_info = cursor.fetchone()  # Fetch the user's information
    conn.close()

    if user_info:
        mut_id, email = user_info
    else:
        mut_id, email = None, None  # Handle case where user is not found

    # Render the home page with the user's information
    return render_template("home.html", mut_id=mut_id, email=email)

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
    # Connect to the database
    conn = sqlite3.connect('stationary.db')
    cursor = conn.cursor()
    
    # Fetch all stationary items
    cursor.execute("SELECT id, name, category, price, stock, image_url, description FROM stationary_items")
    items = cursor.fetchall()
    
    # Close connection
    conn.close()
    
    return render_template('stationary.html', items=items)

@app.route('/product/<int:product_id>')
def product_details(product_id):
    # Fetch product details from your database
    conn = sqlite3.connect('stationary.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stationary_items WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()

    if product:
        return render_template('product_details.html', product=product)
    else:
        return "Product not found", 404


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

    #  Retrieve the order details before deleting
    cursor.execute("SELECT mut_id, copies, layout, print_type, print_sides, expected_datetime FROM print_orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()

    if order:
        #  Print query for debugging
        print("Order found:", order)

        #  Insert into order_history (columns must match exactly)
        cursor.execute("""
            INSERT INTO order_history (mut_id, copies, layout, print_type, print_sides, expected_datetime)
            VALUES (?, ?, ?, ?, ?, ?)
        """, order)

        conn.commit()  # Commit after inserting into history

        #  Now delete only from print_orders
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



@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect('/login')

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (session['user_id'],))
    user = cursor.fetchone()
    conn.close()

    if not user:
        flash('User not found.', 'danger')
        return redirect('/login')

    return render_template('profile.html', user=user)




@app.route('/remove_profile_photo', methods=['POST'])
def remove_profile_photo():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET photo = 'default_profile.png' WHERE mut_id = ?", (session['mut_id'],))
    conn.commit()
    conn.close()
    return redirect(('edit_profile'))



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


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect('/login')

    user_id = session['user_id']

    # Connect to the database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        photo = request.files['photo']

        # Update profile picture if a new one is uploaded
        if photo and allowed_file(photo.filename):
            filename = secure_filename(f"{user_id}_{photo.filename}")
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)

            # Save file path in the database
            cursor.execute("UPDATE users SET photo=? WHERE id=?", (filename, user_id))

        # Update email and password
        cursor.execute("UPDATE users SET email=?, password=? WHERE id=?", (email, password, user_id))

        conn.commit()
        conn.close()

        flash('Profile updated successfully!', 'success')
        return redirect('/edit_profile')

    # Fetch current user data
    cursor.execute("SELECT mut_id, email, photo FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    return render_template('edit_profile.html', user=user)


if __name__ == '__main__':
    app.run(debug=True)