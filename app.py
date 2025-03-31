from flask import Flask, render_template, request, redirect, flash, session,url_for,jsonify
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
from PyPDF2 import PdfReader
from math import ceil


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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

@app.route('/register', methods=['GET', 'POST'])
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



@app.route('/stationary')
def stationary():
    # Connect to the database
    conn = sqlite3.connect('stationary.db')
    cursor = conn.cursor()
    
    # Fetch all stationary items
    cursor.execute("SELECT id, name, category, price, stock, image_url, description, rating FROM stationary_items")
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

    cursor.execute("""
        SELECT t.id, s.name, t.quantity, t.total_cost, t.status, t.purchase_date
        FROM transactions t
        JOIN stationary_items s ON t.product_id = s.id
        WHERE t.user_id = ?
        ORDER BY t.purchase_date DESC
    """, (user_id,))

    orders = cursor.fetchall()
    conn.close()

    return render_template("s_orders.html", orders=orders)

@app.route('/buy_cart_items', methods=['POST'])
def buy_cart_items():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect("stationary.db")
    cursor = conn.cursor()

    # Fetch cart items with product price
    cursor.execute("SELECT c.product_id, c.quantity, s.price FROM cart c JOIN stationary_items s ON c.product_id = s.id WHERE c.user_id = ?", (user_id,))
    cart_items = cursor.fetchall()

    if not cart_items:
        conn.close()
        return redirect(url_for('cart_page'))  # No items in cart, redirect back

    # Insert cart items into transactions table with total cost
    for item in cart_items:
        product_id, quantity, price = item
        total_cost = price * quantity  # Calculate total cost
        cursor.execute("INSERT INTO transactions (user_id, product_id, quantity, total_cost) VALUES (?, ?, ?, ?)",
                       (user_id, product_id, quantity, total_cost))

    # Clear cart after purchase
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('s_orders'))  # Redirect to orders page





if __name__ == '__main__':
    app.run(debug=True)