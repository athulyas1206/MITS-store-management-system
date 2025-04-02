import sqlite3
import pandas as pd
import csv

#i add
def check_table_structure():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users);")
    columns = cursor.fetchall()
    for column in columns:
        print(column)
    conn.close()

check_table_structure()

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mut_id TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
        )
    ''')
    
    try:
       cursor.execute("ALTER TABLE users ADD COLUMN name TEXT NOT NULL;")
    except sqlite3.OperationalError:
        print("Column 'name' already exists.")



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



# Connect to SQLite (this will create 'stationary.db' if it doesn't exist)
conn = sqlite3.connect('stationary.db')

# Create a cursor object to execute SQL commands
cursor = conn.cursor()

# Create the stationary_items table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS stationary_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock INTEGER NOT NULL,
        image_url TEXT,
        description TEXT,
        rating INTEGER DEFAULT 0 CHECK (rating BETWEEN 0 AND 5),
        rating_count INTEGER DEFAULT 0
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1,
        FOREIGN KEY (product_id) REFERENCES stationary_items(id)
    )
''')

# Create transactions table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        total_cost REAL NOT NULL,
        status TEXT DEFAULT 'pending',
        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES stationary_items(id)
    );
    """)
# Create s_order_history table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS s_order_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        total_cost REAL NOT NULL,
        status TEXT DEFAULT 'completed',
        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES stationary_items(id)
    );
""")


# Commit and close the connection
conn.commit()
conn.close()

print("Database and table created successfully!")
print("Cart table created successfully!")
print("transactions table created successfully!")
print("s_order_history table created successfully!")

# Load the CSV file
csv_file = "stationary_products_with_description.csv"
df = pd.read_csv(csv_file)

# Connect to the SQLite database
conn = sqlite3.connect("stationary.db")
cursor = conn.cursor()

# Insert products into the table (WITHOUT manually setting id)
for index, row in df.iterrows():
    cursor.execute("""
        INSERT INTO stationary_items (name, category, price, stock, image_url, description, rating, rating_count) 
        VALUES (?, ?, ?, ?, ?, ?,?,?)
    """, (row["name"], row["category"], row["price"], row["stock"], row["image_url"], row["description"], row["rating"], row["rating_count"]))

# Commit and close the connection
conn.commit()
conn.close()

print("Products inserted successfully!")











if __name__ == '__main__':
    create_user_db()
    create_print_orders()
