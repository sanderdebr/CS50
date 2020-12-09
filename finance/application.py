import os
import logging

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Get all shares of user
    rows = db.execute("SELECT * FROM shares WHERE userId = :id", id=session["user_id"])

    shares = []
    for row in rows:
        logging.info(row)
        symbolInfo = lookup(row["symbol"])
        # Calculate total
        total = symbolInfo["price"] * row["shares"]
        total = format(total, '.2f')
        total = int(float(total))
        share = {
            "symbol": row["symbol"],
            "shares": row["shares"],
            "name": symbolInfo["name"],
            "price": symbolInfo["price"],
            "total": total
        }
        shares.append(share)

    # Calculate user's cash
    rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
    cash = rows[0]["cash"]

    # Calculate total
    total = 0
    for share in shares:
        total += share["total"]
    total += cash

    return render_template("index.html", shares=shares, cash=cash, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        symbolInfo = lookup(symbol)

        # Check if symbol exists
        if (symbolInfo is None):
            return apology("Invalid symbol")

        # Check if shares is positive number
        if shares < 0:  # if not a positive int print message and ask for input again
            return apology("Shares is not a valid number")

        rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        cash = rows[0]["cash"]

        totalCosts = symbolInfo["price"] * shares;
        newCash = cash - totalCosts

        if (totalCosts > cash):
            return apology("Not enough cash")

        db.execute("CREATE TABLE IF NOT EXISTS 'shares' (id INTEGER PRIMARY KEY NOT NULL, userId INTEGER NOT NULL, symbol TEXT NOT NULL, shares INTEGER NOT NULL)")

        db.execute("INSERT INTO shares (userId, symbol, shares) VALUES(:userId,:symbol,:shares)", userId=session["user_id"], symbol=symbol, shares=shares)

        db.execute("UPDATE users SET cash = ? WHERE id = ?", newCash, session["user_id"])

        return redirect("/")

    else:
        return render_template("buy.html");


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

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
    if request.method == "POST":
        symbol = request.form.get("symbol")
        symbolInfo = lookup(symbol)
        if (symbolInfo):
            session["symbol"] = symbolInfo
            return render_template("quoted.html")
        else:
            return apology("Invalid symbol")

    else:
        return render_template("quote.html");


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password") or not request.form.get("password2"):
            return apology("must provide two passwords", 403)

        # Ensure both passwords are the same
        elif not request.form.get("password") == request.form.get("password2"):
            return apology("both passwords must be the same", 403)

        # Add user to the database
        id = db.execute("INSERT INTO users (username, hash) VALUES(:username,:password)",
                            username=request.form.get("username"), password=generate_password_hash(request.form.get("password")))

        # Add user id to session
        session["user_id"] = id

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
