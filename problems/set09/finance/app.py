import os
import datetime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify, json
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, create_table, int_format

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    # db.execute(' UPDATE users SET cash = ? WHERE users.id = ?;', 10000, session['user_id'])

    """Show portfolio of stocks"""
    # Checkif the table exists
    table_exists = db.execute('SELECT name FROM sqlite_master WHERE name = "stockTransactions" AND type="table";')

    # Create the tables if dont exist 
    if not table_exists:
        create_table(db)

    # Select the users stocks information
    stocks = db.execute(
        'SELECT *, SUM(stockPrice * shareQty) AS stockValue FROM stockTransactions WHERE ownerId = ? GROUP BY stockSymbol HAVING shareQty > 0', session['user_id'])

    # Store the sum of all shares value.
    sharesValue = sum([t['stockValue']for t in stocks])

    # Store the user's cash
    cash = db.execute('SELECT cash FROM users WHERE users.id == ?',
                        session['user_id'])[0]['cash']

    return render_template('index.html', usd=usd, stocks=stocks, int_format=int_format, user_cash=cash, stock_value=sharesValue)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    user_id = session['user_id']
    # Set the data to implement the autocomplete feature in javascript
    with open('symbols.json', 'r') as f:
        data = json.load(f)

    # Store the user information
    user_info = db.execute('SELECT * FROM users WHERE id = ?', user_id)[0]
    # Set the username
    user = user_info['username']

    if request.method == 'POST':

        if lookup(request.form.get('symbol')) == None:
            return apology('You have entered an invalid symbol', 400)

        if not request.form.get('shares').isnumeric():
            return apology('No a valid quatity')

        transaction_type = 'Purchased'
        transaction_date = datetime.datetime.now()

        symbol = request.form.get('symbol')
        qty = int(request.form.get('shares'))
        symbol_info = lookup(symbol)

        print(symbol_info, qty)

        company_price = symbol_info['price']
        stocks_value = company_price * qty
        cash = user_info['cash']
        company_name = symbol_info['name']
        cash_left = cash - stocks_value


        symbol_exists = db.execute(
            'SELECT stockSymbol FROM stockTransactions WHERE stockSymbol = ? AND ownerId = ?', symbol, user_id)

        if cash < company_price * qty:
            return apology('NO ENOUGH CASH')

        if len(symbol_exists) > 0:
            db.execute('UPDATE stockTransactions SET shareQty = shareQty + ?, stockPrice = ?  WHERE stockSymbol = ? AND ownerId = ?;',
                        qty, company_price, symbol, user_id)
        else:
            db.execute('INSERT INTO stockTransactions (stockSymbol, stockName, stockPrice, shareQty, ownerId) VALUES (?,?,?,?,?);',
                        symbol, company_name, company_price, qty, user_id)

        db.execute('INSERT INTO transactionHistories (stockSymbol, stockPrice, shareQtySold, transactionDate, transactionType, ownerId) VALUES (?,?,?,?,?,?);', symbol, symbol_info['price'], qty, transaction_date, transaction_type, user_id)

        db.execute('UPDATE users SET cash = cash - ? WHERE id = ?;',
                    stocks_value, user_id)

        return redirect('/')

    return render_template('buy.html', data=data)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    data = db.execute(
        'SELECT * FROM transactionHistories WHERE ownerId = ? ORDER BY transactionDate DESC;', session['user_id'])

    print(data)
    return render_template('history.html', data=data, usd=usd, int_format=int_format)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?",
                            request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    quote = {}
    with open('symbols.json', 'r') as f:
        data = json.load(f)

    if request.method == 'POST':
        if not request.form.get('symbol'):
            return apology('Symbol can\'t be empty', 400)
        elif lookup(request.form.get('symbol')) == None:
            return apology('You have entered an invalid symbol', 400)

        symbol = request.form['symbol']
        quote = lookup(request.form.get('symbol'))

    return render_template('quote.html', data=data, requested_quote=quote, usd=usd)


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == 'POST':
        """Register user"""
        username = request.form.get('username')
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        username_check = db.execute('SELECT username FROM users')

        if not username or not password:
            return apology('No username provided')

        if password != confirmation:
            return apology('Password and password confirmation doesn\'t match')

        for user in username_check:
            if user['username'] == username:
                return apology('This username is already used.')

        hashed_password = generate_password_hash(
            password, method='sha256', salt_length=16)

        db.execute('INSERT INTO users (username, hash) VALUES (?,?)',
                    username, hashed_password)

        # print(username, password, hashed_password)
        return redirect('/')

    return render_template('register.html')


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    shares = db.execute(
        'SELECT * FROM stockTransactions WHERE ownerId = ? AND shareQty > 0', session['user_id'])

    if request.method == 'POST':
        symbol = request.form.get('symbol')
        shares_number = int(request.form.get('shares'))
        transaction_date = datetime.datetime.now()
        transaction_type = 'Sold'

        sold_shares = lookup(symbol)

        isinshare = [d for d in shares if d['stockSymbol'] == symbol]

        current_share_price = isinshare[0]['stockPrice']
        sell_price = sold_shares['price'] * shares_number
      

        remaing_shares = 0
        if not symbol:
            return apology("You did not select a symbol")

        for share in shares:
            if int(shares_number) > share['shareQty'] and share['stockSymbol'] == symbol:
                return apology("Not that many shares")


        db.execute('INSERT INTO transactionHistories (stockSymbol, stockPrice, shareQtySold, transactionDate, transactionType, ownerId) VALUES (?,?,?,?,?,?);', symbol, sold_shares['price'], shares_number, transaction_date, transaction_type, session['user_id'])

        db.execute('UPDATE stockTransactions SET shareQty = shareQty - ? WHERE stockSymbol = ? AND ownerId = ?', 
                    shares_number, symbol, session['user_id'])

        db.execute('UPDATE users SET cash = cash + ? WHERE id = ?',
                    sell_price, session['user_id'])

        return redirect('/')

    return render_template('sell.html', shares=shares)
