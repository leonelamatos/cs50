import os, datetime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify, json
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, create_table, int_format, create_history_table

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
    """Show portfolio of stocks"""

    # create_table(db)
    # create_history_table(db)
    # db.execute(' UPDATE users SET cash = ? WHERE users.id = ?;', 10000, 1)

    user_shares = db.execute('SELECT cash, SUM(price * share_qty) AS sum, symbol,name,price, share_qty FROM users JOIN shares ON owner_id = users.id WHERE users.id = ? ORDER BY purchased_on DESC;', session['user_id'])


    cash = user_shares[0]['cash']
    total_share = user_shares[0]['sum'] or 0


    return render_template('home.html', usd=usd, user_shares=user_shares, int_format=int_format, user_cash=cash, total_share=total_share)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    user_info = db.execute('SELECT * FROM users WHERE id = ?', session['user_id'])
    user_id = user_info[0]['id']
    user = user_info[0]['username']

    with open('symbols.json', 'r') as f:
        data = json.load(f)
    
    if request.method == 'POST':
        symbol = request.form['symbol']
        qty = int(request.form['qty'])
        symbol_info = lookup(symbol)
        company_price = symbol_info['price']
        total_amount = company_price * qty
        cash = user_info[0]['cash']
        company_name = symbol_info['name']
        cash_left = cash - total_amount
        buy_on = datetime.datetime.now()

        symbol_exists = db.execute('SELECT symbol FROM shares WHERE symbol = ? AND owner_id = ?', symbol, user_id)

        if cash < company_price:
            return apology('NO ENOUGH CASH')

        if len(symbol_exists) > 0:
            db.execute('UPDATE shares SET share_qty = share_qty + ?, price = ? WHERE symbol = ?;', qty, company_price, symbol)
            db.execute('UPDATE users SET cash = cash - ? WHERE id = ?;', total_amount, user_id)
            # return
        else:

            db.execute('INSERT INTO shares (symbol,name,price,share_qty,purchased_on, owner_id) VALUES (?,?,?,?,?,?);', symbol, company_name, company_price, qty, buy_on, user_id)

            db.execute('UPDATE users SET cash = cash - ? WHERE id = ?;', total_amount, user_id)

        db.execute('INSERT INTO history (symbol, price,share_qty, transaction_date, type, ownerId) VALUES (?,?,?,?,?,?);', symbol, company_price,qty,buy_on,'Purchased', user_id)

        return redirect('/')

            
    return render_template('buy.html', data=data)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    data = db.execute('SELECT * FROM history WHERE ownerId = ? ORDER BY transaction_date DESC;', session['user_id'])
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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

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
        symbol = request.form['quote']
        quote = lookup(symbol)

    return render_template('quote.html', data=data, requested_quote=quote, usd=usd)


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == 'POST':
        """Register user"""
        username = request.form.get('username')
        password = request.form.get('password')

        hashed_password = generate_password_hash(password, method='sha256',salt_length=16)

        db.execute('INSERT INTO users (username, hash) VALUES (?,?)', username, hashed_password)
        
        # print(username, password, hashed_password)
        return redirect('/')

    return render_template('register.html')


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    shares = db.execute('SELECT * FROM shares WHERE owner_id = ?', session['user_id'])

    if request.method == 'POST':
        symbol = request.form.get('symbol')
        shares_number =  request.form.get('shares')
        sold_on = datetime.datetime.now()

        sold_shares = lookup(symbol)

        if not symbol:
            return apology("You did not select a symbol")

        for share in shares:
            if int(shares_number) > share['share_qty'] and share['symbol'] == symbol:
                return apology("Not that many shares")
            if share['share_qty'] == 0:
                db.execute('DELETE FROM shares WHERE share_qty = 0 AND owner_id = ?;', session['user_id'])

        db.execute('UPDATE shares SET share_qty = share_qty - ?, sold_on = ?  WHERE symbol = ?', shares_number, sold_on, symbol)

        db.execute('UPDATE users SET cash = cash + ? WHERE id = ?', sold_shares['price'], session['user_id'])

        db.execute('INSERT INTO history (symbol, price,share_qty, transaction_date, type, ownerId) VALUES (?,?,?,?,?,?);', symbol, sold_shares['price'],shares_number,sold_on,'Sold', session['user_id'])

        return redirect('/')
            

    return render_template('sell.html', shares=shares)


