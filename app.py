from flask import Flask, render_template, request, redirect, flash, session,url_for,jsonify,g
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
from PyPDF2 import PdfReader
from math import ceil
from recommendation import get_recommendations
from flask_mail import Mail, Message
import random
import re  # Import regex for validation
import pytz

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
            session["admin"] = True  # ✅ This ensures admin session is set
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

@app.route("/print_orders_user")
def print_orders_user():
    if "mut_id" not in session:
        return redirect(url_for("login"))

    mut_id = session["mut_id"]
    conn = sqlite3.connect("print_orders.db")
    cursor = conn.cursor()

    # Fetch active print orders
    cursor.execute("SELECT * FROM print_orders WHERE mut_id = ?", (mut_id,))
    active_orders = cursor.fetchall()

    # Fetch completed print orders
    cursor.execute("SELECT * FROM order_history WHERE mut_id = ?", (mut_id,))
    completed_orders = cursor.fetchall()

    conn.close()

    return render_template("print_orders_user.html", active_orders=active_orders, completed_orders=completed_orders)



@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin.html')

@app.route('/admin_print_orders')
def admin_print_orders():
    # Connect to SQLite
    conn = sqlite3.connect('print_orders.db')
    cursor = conn.cursor()

    # Fetch active print orders
    cursor.execute("""
        SELECT id, mut_id, copies, layout, print_type, print_sides, expected_datetime, pdf_filename, status
        FROM print_orders
        WHERE status != 'Completed'
        ORDER BY expected_datetime ASC
    """)

    orders = cursor.fetchall()
    conn.close()

    return render_template('admin_print_orders.html', orders=orders)

@app.route('/update_print_order/<int:order_id>')
def update_print_order(order_id):
    conn = sqlite3.connect('print_orders.db')
    cursor = conn.cursor()

    # Fetch the order details
    cursor.execute("SELECT * FROM print_orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()

    if order:
        # Move order to order_history
        cursor.execute("""
            INSERT INTO order_history (mut_id, copies, layout, print_type, print_sides, expected_datetime, pdf_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (order[1], order[2], order[3], order[4], order[5], order[6], order[7]))

        # Delete the order from print_orders
        cursor.execute("DELETE FROM print_orders WHERE id = ?", (order_id,))

        conn.commit()

    conn.close()

    return redirect('/admin_print_orders')

@app.route('/admin_print_history')
def admin_print_history():
    conn = sqlite3.connect('print_orders.db')
    cursor = conn.cursor()

    # Fetch all completed print orders from order_history
    cursor.execute("SELECT * FROM order_history ORDER BY id DESC")
    history_orders = cursor.fetchall()

    conn.close()
    return render_template('admin_print_history.html', history_orders=history_orders)




@app.route('/admin_stationary_items')
def admin_stationary_items():
    if "mut_id" not in session or session["mut_id"] != "admin":
        flash("Unauthorized access. Please log in as admin.", "danger")
        return redirect(url_for("login"))

    # Connect to the SQLite database
    conn = sqlite3.connect('stationary.db')
    cursor = conn.cursor()

    # Fetch all items from the stationary_items table
    cursor.execute("SELECT * FROM stationary_items")
    items = cursor.fetchall()

    # Close the connection
    conn.close()

    # Render the template with the items
    return render_template('admin_stationary_items.html', items=items)


@app.route('/admin_stationary_orders')
def admin_stationary_orders():
    # Connect to SQLite
    conn = sqlite3.connect('stationary.db')
    cursor = conn.cursor()

    # Fetch pending stationary orders along with product details
    cursor.execute("""
        SELECT t.id, t.user_id, si.name, t.quantity, t.total_cost, t.status, t.purchase_date
        FROM transactions t
        JOIN stationary_items si ON t.product_id = si.id
        WHERE t.status = 'pending'
    """)
    orders = cursor.fetchall()

    # Close connection
    conn.close()

    return render_template('admin_stationary_orders.html', orders=orders)

@app.route('/update_order/<int:order_id>')
def update_order(order_id):
    # Connect to SQLite
    conn = sqlite3.connect('stationary.db')
    cursor = conn.cursor()

    # Fetch order details before moving to history
    cursor.execute("SELECT * FROM transactions WHERE id = ?", (order_id,))
    order = cursor.fetchone()

    if order:
        # Move order to s_order_history
        cursor.execute("""
            INSERT INTO s_order_history (user_id, product_id, quantity, total_cost, status, purchase_date)
            VALUES (?, ?, ?, ?, 'completed', ?)
        """, (order[1], order[2], order[3], order[4], order[6]))

        # Delete the order from transactions
        cursor.execute("DELETE FROM transactions WHERE id = ?", (order_id,))

        conn.commit()

    conn.close()

    return redirect('/admin_stationary_orders')

@app.route('/admin_stationary_history')
def admin_stationary_history():
    # Connect to SQLite
    conn = sqlite3.connect('stationary.db')
    cursor = conn.cursor()

    # Fetch completed stationary orders
    cursor.execute("""
        SELECT s_order_history.id, s_order_history.user_id, stationary_items.name, 
               s_order_history.quantity, s_order_history.total_cost, s_order_history.purchase_date 
        FROM s_order_history 
        JOIN stationary_items ON s_order_history.product_id = stationary_items.id
        ORDER BY s_order_history.purchase_date DESC
    """)
    
    orders = cursor.fetchall()
    conn.close()

    return render_template('admin_stationary_history.html', orders=orders)


@app.route('/update_status', methods=['POST'])
def update_status():
        order_id = request.form['order_id']
        new_status = request.form['status']

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE print_orders SET status = ? WHERE id = ?", (new_status, order_id))
        conn.commit()
        conn.close()

@app.route('/update_stationary_order/<int:order_id>/<new_status>', methods=['POST'])
def update_stationary_order(order_id, new_status):
    conn = sqlite3.connect('stationary.db')
    cursor = conn.cursor()
    
    # Update the order status
    cursor.execute("UPDATE transactions SET status = ? WHERE id = ?", (new_status, order_id))
    
    # If order is completed, move to s_order_history
    if new_status == 'completed':
        cursor.execute("INSERT INTO s_order_history SELECT * FROM transactions WHERE id = ?", (order_id,))
        cursor.execute("DELETE FROM transactions WHERE id = ?", (order_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route("/update_stock", methods=["POST"])
def update_stock():
    if "admin" not in session:
        flash("Unauthorized access. Please log in as admin.", "danger")
        return redirect(url_for("login"))

    item_id = request.form["id"]
    new_stock = request.form["stock"]

    conn = sqlite3.connect("stationary.db")
    cursor = conn.cursor()

    # ✅ Use correct table name: stationary_items
    cursor.execute("UPDATE stationary_items SET stock = ? WHERE id = ?", (new_stock, item_id))
    conn.commit()
    conn.close()

    flash("Stock updated successfully!", "success")
    return redirect(url_for("admin_stationary_items"))



        
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

        # Calculate total cost
        cost_per_page = 1.5 if print_type == 'black_white' else 5
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

        # # Update profile picture if a new one is uploaded
        # if photo and allowed_file(photo.filename):
        #     filename = secure_filename(f"{user_id}_{photo.filename}")
        #     photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        #     photo.save(photo_path)

            # Save file path in the database
            #cursor.execute("UPDATE users SET photo=? WHERE id=?", (filename, user_id))

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

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect('/login')

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT mut_id, email, photo FROM users WHERE id=?", (session['user_id'],))
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


@app.route('/cancel_order')
def cancel_order():
    # Set a flash message indicating the order has been canceled
    flash('Your order is cancelled.', 'info')
    return redirect(url_for('home'))

@app.route('/stationary')
def stationary():
    conn = sqlite3.connect('stationary.db')
    cursor = conn.cursor()

    user_id = session.get("user_id")

    # Fetch all stationary items sorted by rating
    cursor.execute('''
        SELECT id, name, category, price, stock, image_url, description, rating 
        FROM stationary_items 
        ORDER BY rating DESC
    ''')
    items = cursor.fetchall()

    # Fetch recommended items using AI-based recommendations
    recommended_items = []
    if user_id:
        recommended_product_ids = get_recommendations(user_id, top_n=5)
        
        print("Recommended Product IDs:", recommended_product_ids)  # Debugging line ✅

        if recommended_product_ids:
            query = f'''
                SELECT id, name, category, price, stock, image_url, description, rating
                FROM stationary_items
                WHERE id IN ({",".join("?" * len(recommended_product_ids))})
            '''
            cursor.execute(query, recommended_product_ids)
            recommended_items = cursor.fetchall()
            print("Fetched Recommended Items:", recommended_items)  # Debugging line ✅

    # Fallback: If no personalized recommendations, show trending items
    if not recommended_items:
        cursor.execute('''
            SELECT id, name, category, price, stock, image_url, description, rating
            FROM stationary_items
            ORDER BY rating DESC
            LIMIT 5
        ''')
        recommended_items = cursor.fetchall()

    # Fetch cart count
    cart_count = 0
    orders_count = 0
    if user_id:
        cursor.execute("SELECT COUNT(*) FROM cart WHERE user_id = ?", (user_id,))
        cart_count = cursor.fetchone()[0]

        # Fetch active + completed order count
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (user_id,))
        active_orders = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM s_order_history WHERE user_id = ?", (user_id,))
        completed_orders = cursor.fetchone()[0]

        orders_count = active_orders + completed_orders

    conn.close()
    
    return render_template('stationary.html', 
                           items=items, 
                           recommended_items=recommended_items, 
                           cart_count=cart_count, 
                           orders_count=orders_count)

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

@app.route('/submit_rating/<int:product_id>', methods=['POST'])
def submit_rating(product_id):
    user_rating = int(request.form['user_rating'])  # Get user's rating from form

    # Connect to database
    conn = sqlite3.connect('stationary.db')
    cursor = conn.cursor() 

    # Fetch current rating from the database
    cursor.execute("SELECT rating FROM stationary_items WHERE id = ?", (product_id,))
    result = cursor.fetchone()

    if result:
        old_rating = result[0]  # Get the current rating from DB
        new_rating = ceil((old_rating + user_rating) / 2)  # Compute new rating using ceil

        # Update the database
        cursor.execute("UPDATE stationary_items SET rating = ? WHERE id = ?", 
                       (new_rating, product_id))
        conn.commit()

    conn.close()
    return redirect(url_for('product_details', product_id=product_id))  # Redirect back to product page

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    quantity = int(request.form.get("quantity", 1))  # Get quantity from form, default to 1

    conn = sqlite3.connect("stationary.db")
    cursor = conn.cursor()

    # Check if the product is already in the cart
    cursor.execute("SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
    existing_item = cursor.fetchone()

    if existing_item:
        # If the item exists, update the quantity
        new_quantity = existing_item[0] + quantity
        cursor.execute("UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?", 
                       (new_quantity, user_id, product_id))
    else:
        # If the item does not exist, insert it
        cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", 
                       (user_id, product_id, quantity))

    conn.commit()
    conn.close()

    return redirect(url_for('cart_page'))

@app.route('/cart')
def cart_page():
    
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = sqlite3.connect("stationary.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.id, s.name, s.price, c.quantity 
        FROM cart c 
        JOIN stationary_items s ON c.product_id = s.id 
        WHERE c.user_id = ?
    """, (user_id,))

    cart_items = cursor.fetchall()
    # Calculate the total cost
    
    total_cost = sum(item[2] * item[3] for item in cart_items) if cart_items else 0    
    print("Cart Items:", cart_items)  # Debugging Output
    print("Total Cost:", total_cost)  # Debugging Output

    conn.close()

    return render_template("cart.html", cart_items=cart_items,total_cost=total_cost)

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    new_quantity = int(request.form.get('quantity'))

    conn = sqlite3.connect("stationary.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?", (new_quantity, user_id, product_id))
    conn.commit()
    conn.close()

    return redirect(url_for('cart_page'))

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    # Connect to database
    conn = sqlite3.connect('stationary.db')
    cursor = conn.cursor()

    # Remove the item from the cart table
    cursor.execute("DELETE FROM cart WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('cart_page'))  # Redirect back to cart page

@app.route('/buy', methods=['POST'])
def buy_items():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect("stationary.db")
    cursor = conn.cursor()

    # Buying from cart
    if 'from_cart' in request.form:
        cursor.execute("SELECT product_id, quantity FROM cart WHERE user_id = ?", (user_id,))
        cart_items = cursor.fetchall()

        if not cart_items:
            conn.close()
            return redirect(url_for('cart_page'))

        for product_id, quantity in cart_items:
            cursor.execute("SELECT price FROM stationary_items WHERE id = ?", (product_id,))
            price = cursor.fetchone()[0]
            total_cost = price * quantity

            cursor.execute("""
                INSERT INTO transactions (user_id, product_id, quantity, total_cost)
                VALUES (?, ?, ?, ?)
            """, (user_id, product_id, quantity, total_cost))

        # Clear cart after purchase
        cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))

    # Buying from product details page
    else:
        product_id = request.form.get('product_id')
        quantity = int(request.form.get('quantity'))

        cursor.execute("SELECT price FROM stationary_items WHERE id = ?", (product_id,))
        price = cursor.fetchone()[0]
        total_cost = price * quantity

        cursor.execute("""
            INSERT INTO transactions (user_id, product_id, quantity, total_cost)
            VALUES (?, ?, ?, ?)
        """, (user_id, product_id, quantity, total_cost))

    conn.commit()
    conn.close()

    return redirect(url_for('s_orders'))

@app.route('/s_orders')
def s_orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect("stationary.db")
    cursor = conn.cursor()

    # Fetch ongoing orders from `transactions`
    cursor.execute("""
        SELECT t.id, s.name, t.quantity, t.total_cost, t.status, t.purchase_date
        FROM transactions t
        JOIN stationary_items s ON t.product_id = s.id
        WHERE t.user_id = ?
        ORDER BY t.purchase_date DESC
    """, (user_id,))
    ongoing_orders = cursor.fetchall()

    # Fetch completed orders from `s_order_history`
    cursor.execute("""
        SELECT h.id, s.name, h.quantity, h.total_cost, h.status, h.purchase_date
        FROM s_order_history h
        JOIN stationary_items s ON h.product_id = s.id
        WHERE h.user_id = ?
        ORDER BY h.purchase_date DESC
    """, (user_id,))
    completed_orders = cursor.fetchall()

    conn.close()

    return render_template("s_orders.html", ongoing_orders=ongoing_orders, completed_orders=completed_orders)


@app.route('/buy_cart_items', methods=['POST'])
def buy_cart_items():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect("stationary.db")
    cursor = conn.cursor()

    # Fetch cart items with product price and stock
    cursor.execute("SELECT c.product_id, c.quantity, s.price, s.stock FROM cart c JOIN stationary_items s ON c.product_id = s.id WHERE c.user_id = ?", (user_id,))
    cart_items = cursor.fetchall()

    if not cart_items:
        conn.close()
        return redirect(url_for('cart_page'))  # No items in cart, redirect back

    # Insert cart items into transactions table and update stock
    for item in cart_items:
        product_id, quantity, price, stock = item
        total_cost = price * quantity  # Calculate total cost

        # Ensure stock is available before processing the order
        if stock < quantity:
            flash(f"Not enough stock for Product ID {product_id}. Available: {stock}, Requested: {quantity}", "danger")
            conn.close()
            return redirect(url_for('cart_page'))

        # Insert into transactions table
        cursor.execute("INSERT INTO transactions (user_id, product_id, quantity, total_cost) VALUES (?, ?, ?, ?)",
                       (user_id, product_id, quantity, total_cost))

        # Update stock in stationary_items
        new_stock = stock - quantity
        cursor.execute("UPDATE stationary_items SET stock = ? WHERE id = ?", (new_stock, product_id))

    # Clear cart after purchase
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('s_orders'))  # Redirect to orders page

def move_order_to_history(order_id):
    conn = sqlite3.connect("stationary.db")
    cursor = conn.cursor()

    # Get order details
    cursor.execute("SELECT * FROM transactions WHERE id = ?", (order_id,))
    order = cursor.fetchone()

    if order:
        # Insert into history
        cursor.execute("""
            INSERT INTO s_order_history (user_id, product_id, quantity, total_cost, status, purchase_date)
            VALUES (?, ?, ?, ?, 'completed', ?)
        """, (order[1], order[2], order[3], order[4], order[6]))

        # Delete from transactions
        cursor.execute("DELETE FROM transactions WHERE id = ?", (order_id,))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    app.run(debug=True)