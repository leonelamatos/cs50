import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session, jsonify
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def create_table(db):
    db.execute('''
        CREATE TABLE IF NOT EXISTS shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            symbol TEXT NOT NULL,
            name TEXT NOT NULL,
            price NUMERIC NOT NULL,
            share_qty REAL NOT NULL,
            purchased_on TEXT,
            sold_on TEXT,
            owner_id INTEGER,
            FOREIGN KEY (owner_id)
            REFERENCES users (id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )'''
    )

def int_format(value):
    return int(value)







# def search_symbol(query):
#     try:
#         api_key = os.environ.get("API_ACCESS_KEY")
#         url = f'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey={api_key}'
#         response = requests.get(url)
#         response.raise_for_status()
#     except requests.RequestException:
#         return None

#     try:
#         raw_query = response.json()
#         query = raw_query["bestMatches"]
#         filtered =  [c for c in query if condition(c)]
#         return filtered
        
#     except  (KeyError, TypeError, ValueError):
#         return None


# 