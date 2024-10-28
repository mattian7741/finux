from datetime import datetime, timedelta
import calendar
from flask import Flask, render_template, request, jsonify, g
import sqlite3

app = Flask(__name__)
DATABASE = '../finances/financials.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def generate_date_range(start_date, end_date, bucket_size):
    date_list = []
    current_date = start_date

    if bucket_size == 'day':
        while current_date <= end_date:
            date_list.append((current_date.strftime('%Y-%m-%d'), current_date.strftime('%Y-%m-%d')))
            current_date += timedelta(days=1)
    elif bucket_size == 'week':
        while current_date <= end_date:
            week_start = current_date - timedelta(days=current_date.weekday())  # Start of the week (Monday)
            week_end = week_start + timedelta(days=6)  # End of the week (Sunday)
            date_list.append((week_start.strftime('%Y-%m-%d'), week_end.strftime('%Y-%m-%d')))
            current_date = week_end + timedelta(days=1)
    elif bucket_size == 'month':
        while current_date <= end_date:
            month_start = current_date.replace(day=1)
            next_month = month_start.month % 12 + 1
            year_increment = (month_start.month + 1) // 13
            month_end = (month_start.replace(month=next_month, year=month_start.year + year_increment) - timedelta(days=1))
            date_list.append((month_start.strftime('%Y-%m-%d'), month_end.strftime('%Y-%m-%d')))
            current_date = month_end + timedelta(days=1)

    return date_list

@app.route('/data_combined')
def data_combined():
    start_date = request.args.get('startDate') or datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')
    end_date = request.args.get('endDate') or datetime.now().strftime('%Y-%m-%d')
    bucket_size = request.args.get('bucketSize', 'day')
    selected_categories = request.args.getlist('tx_category')
    selected_accounts = request.args.getlist('account')  # New: Get selected accounts

    db = get_db()
    
    # Generate full date ranges
    date_ranges = generate_date_range(datetime.strptime(start_date, '%Y-%m-%d'), datetime.strptime(end_date, '%Y-%m-%d'), bucket_size)
    
    # Base query and parameters
    query = "SELECT SUM(tx_amount) AS amount FROM all_transactions WHERE tx_date BETWEEN ? AND ?"
    params = [start_date, end_date]

    # Adjust query to include category and account filtering if provided
    if selected_categories:
        placeholders = ','.join('?' * len(selected_categories))
        query += f" AND tx_category IN ({placeholders})"
        params.extend(selected_categories)
    
    if selected_accounts:
        placeholders = ','.join('?' * len(selected_accounts))
        query += f" AND Account IN ({placeholders})"
        params.extend(selected_accounts)

    result = []
    for range_start, range_end in date_ranges:
        # Update the date range for each period while keeping category and account params if applicable
        query_params = [range_start, range_end] + (selected_categories if selected_categories else []) + (selected_accounts if selected_accounts else [])
        total = db.execute(query, query_params).fetchone()["amount"]
        result.append({'date': range_start, 'amount': total if total is not None else 0})

    return jsonify(result)

@app.route('/data')
def data():
    selected_categories = request.args.getlist('tx_category')
    selected_accounts = request.args.getlist('account')  # New: Get selected accounts
    start_date = request.args.get('startDate') or datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')
    end_date = request.args.get('endDate') or datetime.now().strftime('%Y-%m-%d')
    bucket_size = request.args.get('bucketSize', 'day')

    db = get_db()

    # If no categories are selected, include all categories
    if not selected_categories:
        selected_categories = [row['tx_category'] for row in db.execute("SELECT DISTINCT tx_category FROM all_transactions")]

    # Generate date ranges based on bucket size
    date_ranges = generate_date_range(datetime.strptime(start_date, '%Y-%m-%d'), datetime.strptime(end_date, '%Y-%m-%d'), bucket_size)

    # Prepare data for each selected category
    result = {}
    for category in selected_categories:
        category_data = []
        for range_start, range_end in date_ranges:
            query = """
                SELECT SUM(tx_amount) AS amount
                FROM all_transactions
                WHERE tx_date BETWEEN ? AND ? AND tx_category = ?
            """
            query_params = [range_start, range_end, category]
            
            # Add account filter if accounts are selected
            if selected_accounts:
                placeholders = ','.join('?' * len(selected_accounts))
                query += f" AND Account IN ({placeholders})"
                query_params.extend(selected_accounts)
                
            total = db.execute(query, query_params).fetchone()["amount"]
            category_data.append({'date': range_start, 'amount': total if total is not None else 0})
        result[category] = category_data

    return jsonify(result)


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/')
def home():
    start_date = request.args.get('startDate') or datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')
    end_date = request.args.get('endDate') or datetime.now().strftime('%Y-%m-%d')
    selected_categories = request.args.getlist('tx_category')
    selected_accounts = request.args.getlist('account')  # New: get selected accounts
    
    db = get_db()
    params = [start_date, end_date]

    # Adjust query to filter transactions by date range, categories, and accounts if specified
    query = 'SELECT * FROM all_transactions WHERE tx_date BETWEEN ? AND ?'
    
    if selected_categories:
        placeholders = ','.join('?' * len(selected_categories))
        query += f' AND tx_category IN ({placeholders})'
        params.extend(selected_categories)
        
    if selected_accounts:  # New: Add filtering for accounts
        placeholders = ','.join('?' * len(selected_accounts))
        query += f' AND Account IN ({placeholders})'
        params.extend(selected_accounts)

    # Fetch transactions within date range, selected categories, and selected accounts (if any)
    transactions = db.execute(query, params).fetchall()

    # Calculate the total amount within the selected date range, categories, and accounts
    sum_query = 'SELECT SUM(tx_amount) FROM all_transactions WHERE tx_date BETWEEN ? AND ?'
    if selected_categories:
        sum_query += f' AND tx_category IN ({placeholders})'
    if selected_accounts:
        sum_query += f' AND Account IN ({placeholders})'
    total_amount = db.execute(sum_query, params).fetchone()[0] or 0

    # Fetch distinct categories and accounts for filter options
    categories = db.execute('SELECT DISTINCT tx_category FROM all_transactions WHERE tx_category IS NOT NULL ORDER BY tx_category').fetchall()
    accounts = db.execute('SELECT DISTINCT Account FROM all_transactions WHERE Account IS NOT NULL ORDER BY Account').fetchall()  # New: Fetch accounts

    return render_template(
        'transactions.html',
        transactions=transactions,
        categories=categories,
        accounts=accounts,  # New: Pass accounts to template
        selected_categories=selected_categories,
        selected_accounts=selected_accounts,  # New: Pass selected accounts to template
        total_amount=total_amount,
        start_date=start_date,
        end_date=end_date
    )


@app.route('/merchants')
def merchants():
    db = get_db()
    # Fetch all columns including tx_category from the merchant table
    merchants = db.execute('SELECT merchant_id, city, region, country, phone_number, url, category, tx_category FROM merchant').fetchall()
    return render_template('merchants.html', merchants=merchants)

@app.route('/update_category', methods=['POST'])
def update_category():
    data = request.get_json()
    merchant_id = data.get('merchant_id')
    category = data.get('category')

    db = get_db()
    # Update only the 'category' field in the merchant table
    db.execute(
        'UPDATE merchant SET category = ? WHERE merchant_id = ?',
        (category, merchant_id)
    )
    db.commit()
    return jsonify({'success': True})

@app.route('/merchant_detail')
def merchant_detail():
    merchant_id = request.args.get('merchant_id')
    db = get_db()
    cursor = db.cursor()

    # Prepare SQL query and log it for debugging
    query = "SELECT * FROM all_transactions WHERE tx_merchant = ?"
    print(f"Executing SQL query: {query} with merchant_id: {merchant_id}")
    
    # Execute the query
    cursor.execute(query, (merchant_id,))
    transactions = cursor.fetchall()
    db.close()

    return render_template('merchant_detail.html', merchant_id=merchant_id, transactions=transactions)

if __name__ == '__main__':
    app.run(debug=True)
