import os

from flask import Flask, session, render_template, request, url_for, redirect
from flask_session.__init__ import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
import requests


app = Flask(__name__)


'''
Steps to do to make it work:

write to terminal the following to export db: 
export DATABASE_URL="postgres://ivtrjlpbpcgdxj:c80c533c0fb06a92d050e92c5f2c0a14ea611513da93debd4f958eb2ddd65bf8@ec2-52-23-14-156.compute-1.amazonaws.com:5432/d2g7skcsq6iqt8"

goodread key: Uw3116lRPgUjSYfVVbA

Depreciate werkzeug:
$ pip uninstall werkzeug
$ pip install werkzeug==0.16.0

Install the following besides the requirements.txt 
pip install psycopg2-binary

'''

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


def login_required(f):
    """
    Decorate routes to require login.
    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def index():
    session.clear()
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    # Register new account

    # Forget any user_id
    session.clear()
    
    if request.method == "POST":
        # Ensure there is a username
        if not request.form.get('username'):
            return render_template('register.html', error="Please provide a username")
        elif not request.form.get('password'):
            return render_template('register.html', error="Please provide a password")


        # Query db for username
        user_check = db.execute("SELECT * from users WHERE username = :username", {"username": request.form.get('username')}).fetchone()

        if user_check:
            return render_template('register.html', error='Username already taken')

        hashed_pw = generate_password_hash(request.form.get('password'))

        db.execute("INSERT INTO users (username, pw) VALUES (:username, :password)", {"username": request.form.get('username'), "password":hashed_pw})

        # Commit to db
        db.commit()

        return redirect('/')
    else:
        return render_template('register.html')

@app.route("/login", methods=['GET', 'POST'])
def login():

    session.clear()

    if request.method == "POST":

        if not request.form.get('username'):
            return render_template('login.html', error="Please provide your username")
        elif not request.form.get('password'):
            return render_template('login.html', error="Please enter your password")
        
        row = db.execute("SELECT * from users WHERE username = :username", {"username": request.form.get('username')})
        user_check = row.fetchone()

        if user_check == None or not check_password_hash(user_check[2], request.form.get('password')):
            return render_template('login.html', error="Invalid username and/or password")

        # remember logged in user
        session["user_id"] = user_check[0]
        session["user_name"] = user_check[1]

        return redirect(url_for('search'))
    
    else:
        return render_template('login.html')

@app.route("/logout", methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route("/search", methods=['GET', 'POST'])
@login_required
def search():

    if request.method == "POST":

        if not request.form.get('reference'):
            return render_template('search.html', error='Please provide a title, author or ISBN number')
        query = '%' + request.form.get('reference') + '%'

        query = query.title()

        rows = db.execute("SELECT isbn, title, author, year FROM books WHERE isbn LIKE :query OR title LIKE :query OR author LIKE :query LIMIT 30", {"query": query})

        if rows.rowcount == 0:
            return render_template('search.html', error="There is no book that match your search in our database")

        books = rows.fetchall()
        return render_template('results.html', books=books)
    
    else:
        return render_template('search.html')


@app.route('/book/<isbn>', methods=['GET', 'POST'])
@login_required
def book(isbn):

    if request.method == "GET":
        row = db.execute("SELECT id, isbn, title, author, year FROM books WHERE isbn = :isbn", {'isbn': isbn})

        db_info = row.fetchall()[0]

        key = os.getenv('GOODREAD_APIKEY')

        gr_info = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": isbn}).json()['books'][0]

        reviews = db.execute("SELECT users.username, rating, comment FROM users INNER JOIN reviews ON users.user_id = reviews.user_id WHERE book_id = :book_id", {'book_id':db_info[0]}).fetchall()

        return render_template('book.html', db_info=db_info, gr_info=gr_info, isbn=isbn, reviews=reviews)

    else:
        curr_user = session['user_id']

        book_info = db.execute("SELECT id, isbn FROM books WHERE isbn = :isbn", {'isbn' : isbn}).fetchall()[0]


        # check if the user alread rate this book
        row = db.execute('SELECT * FROM reviews WHERE user_id = :user_id AND book_id = :book_id', {"user_id": curr_user, "book_id": book_info[0]})
        review_info = row.fetchall()
        
        if len(review_info) > 0:
            row = db.execute("SELECT id, isbn, title, author, year FROM books WHERE isbn = :isbn", {'isbn': isbn})
            db_info = row.fetchall()[0]
            key = os.getenv('GOODREAD_APIKEY')
            gr_info = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": isbn}).json()['books'][0]
            reviews = db.execute("SELECT users.username, rating, comment FROM users INNER JOIN reviews ON users.user_id = reviews.user_id WHERE book_id = :book_id", {'book_id':db_info[0]}).fetchall()
            return render_template('book.html', db_info=db_info, gr_info=gr_info, error='You have already reviewed this book !', isbn=isbn, reviews=reviews)

        comment = request.form.get('comment')
        rating = request.form.get('rating')

        db.execute('INSERT INTO reviews (book_id, user_id, rating, comment) VALUES (:book_id, :user_id, :rating, :comment)', {'book_id':book_info[0], 'user_id':curr_user, 'rating':rating, 'comment':comment})
        db.commit()

        row = db.execute("SELECT id, isbn, title, author, year FROM books WHERE isbn = :isbn", {'isbn': isbn})
        db_info = row.fetchall()[0]
        key = os.getenv('GOODREAD_APIKEY')
        gr_info = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": isbn}).json()['books'][0]
        reviews = db.execute("SELECT users.username, rating, comment FROM users INNER JOIN reviews ON users.user_id = reviews.user_id WHERE book_id = :book_id", {'book_id':db_info[0]}).fetchall()
        return render_template('book.html', db_info=db_info, gr_info=gr_info, error="You have successfully added your review !", reviews=reviews)


@app.route('/reviews', methods=['GET'])
@login_required
def reviews():
    return render_template('reviews.html')        

