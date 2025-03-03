import sqlite3

def create_user_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mut_id TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()   # Save changes
    conn.close() 

def create_print_orders():
    conn = sqlite3.connect('print_orders.db')
    cursor = conn.cursor()

    # Create print_orders table (if not already created)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS print_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mut_id TEXT NOT NULL,
            copies INTEGER NOT NULL,
            layout TEXT NOT NULL,
            print_type TEXT NOT NULL,
            print_sides TEXT NOT NULL,
            expected_datetime TEXT NOT NULL,
            pdf_filename TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    ''')

    # Add num_pages column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE print_orders ADD COLUMN num_pages INTEGER;")
    except sqlite3.OperationalError:
        print("Column 'num_pages' already exists.")

    # Add total_cost column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE print_orders ADD COLUMN total_cost INTEGER;")
    except sqlite3.OperationalError:
        print("Column 'total_cost' already exists.")

    # Create closed_dates table for admin to block submission dates
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS closed_dates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL
        )
    ''')

    # Create deleted_orders table to store deleted print orders
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mut_id TEXT NOT NULL,
    copies INTEGER NOT NULL,
    layout TEXT NOT NULL,
    print_type TEXT NOT NULL,
    print_sides TEXT NOT NULL,
    expected_datetime TEXT NOT NULL,
    pdf_filename TEXT NOT NULL
     );
        
    ''')

    conn.commit()   # Save changes
    conn.close() 
    
def delete_print_order(order_id):
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect('print_orders.db')
        cursor = conn.cursor()

        # First, insert the order into order_history table
        cursor.execute('''
            INSERT INTO order_history (mut_id, copies, layout, print_type, print_sides, expected_datetime, pdf_filename)
            SELECT mut_id, copies, layout, print_type, print_sides, expected_datetime, pdf_filename
            FROM print_orders
            WHERE id = ?
        ''', (order_id,))

        # Now, delete the order from the print_orders table
        cursor.execute('''
            DELETE FROM print_orders WHERE id = ?
        ''', (order_id,))

        # Commit the transaction
        conn.commit()

        print(f"Order with ID {order_id} has been moved to order_history and deleted from print_orders.")
    except sqlite3.Error as e:
        print(f"Error occurred while deleting order: {e}")
    finally:
        # Close the connection
        conn.close()


def initialize_db():
    conn = sqlite3.connect('print_orders.db')
    cursor = conn.cursor()

    # Create Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            image TEXT,
            category TEXT,
            stock INTEGER NOT NULL
        );
    ''')

    # Create Transactions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            purchase_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    ''')

    conn.commit()
    conn.close()

def add_sample_products():
    conn = sqlite3.connect('print_orders.db')
    cursor = conn.cursor()

    # Sample Data for Products Table
    sample_products = [
        ('Pen', 'Ballpoint pen with smooth ink flow', 10.0, 'pen.jpg', 'Stationary', 100),
        ('Notebook', 'A5 size notebook with ruled pages', 50.0, 'notebook.jpg', 'Stationary', 50),
        ('Marker', 'Permanent marker with bold ink', 30.0, 'marker.jpg', 'Stationary', 80),
        ('Eraser', 'Non-dust eraser for clean erasing', 5.0, 'eraser.jpg', 'Stationary', 200),
        ('Pencil', 'HB graphite pencil', 3.0, 'pencil.jpg', 'Stationary', 150)
    ]

    # Insert Sample Data
    cursor.executemany('''
        INSERT INTO products (name, description, price, image, category, stock)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', sample_products)

    conn.commit()   # Save changes
    conn.close()    # Close connection

if __name__ == '__main__':
    create_user_db()
    create_print_orders()
    initialize_db()
    add_sample_products()
