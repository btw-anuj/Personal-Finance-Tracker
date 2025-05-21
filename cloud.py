from flask import Flask, render_template, request, redirect, url_for, session
from flask_pymongo import PyMongo
from collections import defaultdict
import os
import numpy as np
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'this_is_a_secret_key_anuj123'

# Add this with your actual MongoDB Atlas URI
app.config["MONGO_URI"] = "mongodb+srv://dbanuj:dbbtwanuj@cloud.hldzbet.mongodb.net/Cloud?retryWrites=true&w=majority"

mongo = PyMongo(app)

print("MongoDB URI:", app.config["MONGO_URI"])


# Ensure templates folder exists
os.makedirs("templates", exist_ok=True)

# Write HTML templates if not already present
templates = {
    "login.html": '''
    <html><body>
        <h2>Login</h2>
        <form method="POST">
            Email: <input type="email" name="email" required><br>
            <button type="submit">Login</button>
        </form>
        <p>New user? <a href="/register">Register here</a></p>
    </body></html>
    ''',
    "register.html": '''
    <html><body>
        <h2>Register</h2>
        <form method="POST">
            Email: <input type="email" name="email" required><br>
            <button type="submit">Register</button>
        </form>
        <p>Already registered? <a href="/login">Login</a></p>
    </body></html>
    ''',
    "dashboard.html": '''
    <html><body>
        <h2>Dashboard</h2>
        <p>Total Income: ₹{{ income }}</p>
        <p>Total Expense: ₹{{ expense }}</p>
        <p><strong>Balance: ₹{{ balance }}</strong></p>
        <p><a href="/add">Add Transaction</a> | <a href="/logout">Logout</a></p>
    </body></html>
    ''',
    "add_transaction.html": '''
    <html><body>
        <h2>Add Transaction</h2>
        <form method="POST">
            Type:
            <select name="type">
                <option value="income">Income</option>
                <option value="expense">Expense</option>
            </select><br>
            Amount: <input type="number" name="amount" step="0.01" required><br>
            Category: <input type="text" name="category" required><br>
            Date: <input type="date" name="date"><br>
            <button type="submit">Add</button>
        </form>
        <p><a href="/dashboard">Back to Dashboard</a></p>
    </body></html>
    '''
}

for filename, content in templates.items():
    filepath = os.path.join("templates", filename)
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            f.write(content)

# Home route
@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        user = mongo.db.users.find_one({'email': email})
        if user:
            session['user'] = user['email']
            return redirect(url_for('dashboard'))
        else:
            return "User not found!"
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    transactions = list(mongo.db.transactions.find({'user': session['user']}))

    income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    expense = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    balance = income - expense

    # AI-based anomaly detection
    income_amounts = [t['amount'] for t in transactions if t['type'] == 'income']
    expense_amounts = [t['amount'] for t in transactions if t['type'] == 'expense']

    income_mean = np.mean(income_amounts) if income_amounts else 0
    income_std = np.std(income_amounts) if income_amounts else 0
    expense_mean = np.mean(expense_amounts) if expense_amounts else 0
    expense_std = np.std(expense_amounts) if expense_amounts else 0

    anomalies = []
    for t in transactions:
        if t['type'] == 'income' and t['amount'] > income_mean + 2 * income_std:
            anomalies.append(t)
        elif t['type'] == 'expense' and t['amount'] > expense_mean + 2 * expense_std:
            anomalies.append(t)

    return render_template(
        'dashboard.html',
        income=income,
        expense=expense,
        balance=balance,
        transactions=transactions,
        anomalies=anomalies
    )

# Add transaction route
from datetime import datetime  # Ensure this is imported at the top

@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        txn_type = request.form['type']
        amount = float(request.form['amount'])
        category = request.form['category']
        date = request.form['date'] or datetime.now().strftime('%Y-%m-%d')

        transaction = {
            'user': session['user'],
            'type': txn_type,
            'amount': amount,
            'category': category,
            'date': date
        }

        mongo.db.transactions.insert_one(transaction)
        print("Transaction added:", transaction)  # For debugging
        return redirect(url_for('dashboard'))

    return render_template('add_transaction.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        existing_user = mongo.db.users.find_one({'email': email})

        if existing_user:
            return "User already exists!"

        mongo.db.users.insert_one({'email': email})
        return redirect(url_for('login'))

    return render_template('register.html')
# summary route
@app.route('/summary')
def summary():
    if 'user' not in session:
        return redirect(url_for('login'))

    transactions = list(mongo.db.transactions.find({'user': session['user']}))

    monthly_data = defaultdict(lambda: {'income': 0, 'expense': 0, 'categories': defaultdict(float)})

    for txn in transactions:
        month = datetime.strptime(txn['date'], '%Y-%m-%d').strftime('%B %Y')
        if txn['type'] == 'income':
            monthly_data[month]['income'] += txn['amount']
        else:
            monthly_data[month]['expense'] += txn['amount']
            monthly_data[month]['categories'][txn['category']] += txn['amount']

    summaries = []
    for month, data in monthly_data.items():
        top_category = max(data['categories'], key=data['categories'].get, default='N/A')
        summaries.append({
            'month': month,
            'income': data['income'],
            'expense': data['expense'],
            'top_category': top_category
        })

    return render_template('summary.html', summaries=summaries)



if __name__ == '__main__':
    app.run(debug=True)
