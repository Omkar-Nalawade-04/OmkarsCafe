from flask import Flask, render_template, request, redirect, session, url_for, flash
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'Omkarscafe'

# Database Configuration -- add database details
db_config = {
    'host': '###',
    'user': '###',
    'password': '###',
    'database': '###'
}

# Database Connection Function
def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/menu')
def menu():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return render_template("menu.html", products=products)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    success = False
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO contact_messages (name, email, message) VALUES (%s, %s, %s)",
                       (name, email, message))
        conn.commit()
        conn.close()
        success = True

    return render_template('contact.html', success=success)

@app.route('/order', methods=['GET', 'POST'])
def order():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    if request.method == 'POST':
        # Get basic customer info
        customer_name = request.form['name']
        contact = request.form['contact']
        address = request.form['address']
        selected_item_names = request.form.getlist('selected_items[]')  # note: [] from HTML

        if not selected_item_names:
            flash('Please select at least one item.', 'warning')
            conn.close()
            return redirect(url_for('order'))

        selected_items = []
        total_price = 0

        for item_name in selected_item_names:
            qty_str = request.form.get(f'quantity_{item_name}', '0')
            try:
                quantity = int(qty_str)
            except ValueError:
                quantity = 0

            cursor.execute("SELECT price FROM products WHERE name = %s", (item_name,))
            product = cursor.fetchone()

            if product and quantity > 0:
                price = product['price']
                item_total = quantity * price
                total_price += item_total
                selected_items.append(f"{item_name} x{quantity} (₹{item_total})")

        if not selected_items:
            flash('Please select at least one valid item with quantity.', 'warning')
            conn.close()
            return redirect(url_for('order'))

        items_str = ', '.join(selected_items)

        # (Optional but safe) Override with frontend total if it matches calculated total
        form_total = float(request.form.get('total_price', total_price))
        total_price = max(total_price, form_total)  # Use whichever is higher to avoid undercharge

        # Insert into DB
        cursor.execute(
            "INSERT INTO orders (customer_name, contact, address, items, total_price) VALUES (%s, %s, %s, %s, %s)",
            (customer_name, contact, address, items_str, total_price)
        )
        conn.commit()
        conn.close()

        flash('Order placed successfully!', 'success')
        return redirect(url_for('order'))

    conn.close()
    return render_template('order.html', products=products)

# ---------- Admin Routes ----------

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Invalid username or password.'
            return render_template('admin_login.html', error=error)

    return render_template('admin_login.html')

@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, customer_name, contact, items, total_price, created_at FROM orders ORDER BY id DESC LIMIT 10")
    recent_orders = cursor.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', recent_orders=recent_orders)

@app.route('/admin/messages')
def view_messages():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM contact_messages ORDER BY created_at DESC")
    messages = cursor.fetchall()
    conn.close()
    return render_template('admin_messages.html', messages=messages)

@app.route('/admin-products')
def admin_products():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return render_template('admin_products.html', products=products)

@app.route('/admin-products/add', methods=['GET', 'POST'])
def add_product():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image = request.form['image']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (name, description, price, image) VALUES (%s, %s, %s, %s)",
                       (name, description, price, image))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_products'))

    return render_template('add_product.html')

@app.route('/admin-products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()
    conn.close()
    flash("Product deleted successfully!", "success")
    return redirect(url_for('admin_products'))

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))
    conn.commit()
    conn.close()
    flash("Order deleted successfully!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/messages/delete/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contact_messages WHERE id = %s", (message_id,))
    conn.commit()
    conn.close()
    flash("Message deleted successfully!", "success")
    return redirect(url_for('view_messages'))

if __name__ == '__main__':
    app.run(debug=True)
