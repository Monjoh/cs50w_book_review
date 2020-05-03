import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv('DATABASE_URL'))
db = scoped_session(sessionmaker(bind=engine))

def main():

    db.execute("CREATE TABLE users (user_id SERIAL PRIMARY KEY, username VARCHAR NOT NULL, pw VARCHAR NOT NULL);")

    db.execute("CREATE TABLE reviews (review_id SERIAL NOT NULL,book_id INTEGER REFERENCES books(id), user_id INTEGER REFERENCES users(user_id), rating INTEGER NOT NULL, comment VARCHAR);")

    """
    db.execute("CREATE TABLE books (id SERIAL PRIMARY KEY, isbn VARCHAR NOT NULL, title VARCHAR NOT NULL, author VARCHAR NOT NULL, year VARCHAR NOT NULL);")
    
    # Do not forget to change to delete the header of the file so it is not included in the db
    b = open('books.csv')
    reader = csv.reader(b)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)", {'isbn': isbn, 'title': title, 'author': author, 'year': year})

        print(f'Added book from {title} released in {year}.')
    
    """
    
    db.commit()

if __name__ == "__main__":
    main()