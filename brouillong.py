@app.route("/book/<isbn>", methods=['GET','POST'])
@login_required
def book(isbn):
    """ Save user review and load same page with reviews updated."""

    if request.method == "POST":

        # Save current user info
        currentUser = session["user_id"]
        
        # Fetch form data
        rating = request.form.get("rating")
        comment = request.form.get("comment")
        
        # Search book_id by ISBN
        row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})

        # Save id into variable
        bookId = row.fetchone() # (id,)
        bookId = bookId[0]

        # Check for user submission (ONLY 1 review/user allowed per book)
        row2 = db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND book_id = :book_id",
                    {"user_id": currentUser,
                     "book_id": bookId})

        # A review already exists
        if row2.rowcount == 1:
            
            flash('You already submitted a review for this book', 'warning')
            return redirect("/book/" + isbn)

        # Convert to save into DB
        rating = int(rating)

        db.execute("INSERT INTO reviews (user_id, book_id, comment, rating) VALUES \
                    (:user_id, :book_id, :comment, :rating)",
                    {"user_id": currentUser, 
                    "book_id": bookId, 
                    "comment": comment, 
                    "rating": rating})

        # Commit transactions to DB and close the connection
        db.commit()

        flash('Review submitted!', 'info')

        return redirect("/book/" + isbn)
    
    # Take the book ISBN and redirect to his page (GET)
    else:

        row = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn = :isbn",
                        {"isbn": isbn})

        bookInfo = row.fetchall()

        """ GOODREADS reviews """

        # Read API key from env variable
        key = os.getenv("GOODREADS_KEY")
        
        # Query the api with key and ISBN as parameters
        query = requests.get("https://www.goodreads.com/book/review_counts.json",
                params={"key": key, "isbns": isbn})

        # Convert the response to JSON
        response = query.json()

        # "Clean" the JSON before passing it to the bookInfo list
        response = response['books'][0]

        # Append it as the second element on the list. [1]
        bookInfo.append(response)

        """ Users reviews """

         # Search book_id by ISBN
        row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})

        # Save id into variable
        book = row.fetchone() # (id,)
        book = book[0]

        # Fetch book reviews
        # Date formatting (https://www.postgresql.org/docs/9.1/functions-formatting.html)
        results = db.execute("SELECT users.username, comment, rating, \
                            to_char(time, 'DD Mon YY - HH24:MI:SS') as time \
                            FROM users \
                            INNER JOIN reviews \
                            ON users.id = reviews.user_id \
                            WHERE book_id = :book \
                            ORDER BY time",
                            {"book": book})

        reviews = results.fetchall()

        return render_template("book.html", bookInfo=bookInfo, reviews=reviews)


