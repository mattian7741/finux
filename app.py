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

@app.route('/data')
def data():
    selected_categories = request.args.getlist('tx_category')
    start_date = request.args.get('startDate') or datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')
    end_date = request.args.get('endDate') or datetime.now().strftime('%Y-%m-%d')
    bucket_size = request.args.get('bucketSize', 'day')

    db = get_db()
    params = [start_date, end_date]

    if selected_categories:
        placeholders = ', '.join(['?'] * len(selected_categories))
        category_filter = f" AND tx_category IN ({placeholders})"
        params.extend(selected_categories)
    else:
        category_filter = ""

    # Generate full date ranges
    date_ranges = generate_date_range(datetime.strptime(start_date, '%Y-%m-%d'), datetime.strptime(end_date, '%Y-%m-%d'), bucket_size)

    # Aggregate data into each bucket based on the generated date ranges
    result = []
    for range_start, range_end in date_ranges:
        query = f"""
            SELECT SUM(tx_amount) AS amount
            FROM all_transactions
            WHERE tx_date BETWEEN ? AND ? {category_filter}
        """
        total = db.execute(query, (range_start, range_end, *selected_categories)).fetchone()["amount"]
        result.append({'date': range_start, 'amount': total if total is not None else 0})

    return jsonify(result)

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/')
def home():
    categories = query_db('SELECT DISTINCT tx_category FROM all_transactions WHERE tx_category IS NOT NULL ORDER BY tx_category')
    selected_categories = request.args.getlist('tx_category')
    
    if selected_categories:
        placeholders = ','.join('?' * len(selected_categories))
        query = f'SELECT * FROM all_transactions WHERE tx_category IN ({placeholders})'
        sum_query = f'SELECT SUM(tx_amount) FROM all_transactions WHERE tx_category IN ({placeholders})'
        transactions = query_db(query, selected_categories)
        total_amount = query_db(sum_query, selected_categories, one=True)[0]
    else:
        transactions = query_db('SELECT * FROM all_transactions')
        total_amount = query_db('SELECT SUM(tx_amount) FROM all_transactions', one=True)[0]

    return render_template('transactions.html', transactions=transactions, categories=categories, selected_categories=selected_categories, total_amount=total_amount)

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


if __name__ == '__main__':
    app.run(debug=True)
