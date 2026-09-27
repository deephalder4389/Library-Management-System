
# Library Management System

A web-based Library Management System developed using Python
and Django to manage books, readers, book issuance, and returns
through a user-friendly interface.

## Technologies Used

- Backend: Python, Django
- Frontend: HTML, CSS, Bootstrap
- Database: SQLite
- Tools: VS Code, Git, GitHub

## Features

### Reader Management
- Register new readers
- Search and update reader details
- Activate and deactivate readers
- Delete reader records

### Book Management
- Upload books with cover images and PDF files
- Search books by title or author
- View uploaded PDF files
- Delete books

### Book Issue and Return
- Add books to My Bag
- Issue books to registered readers
- Track checkout and return due dates
- Return issued books
- Maintain borrowing history

### Administration
- Django Admin panel
- Manage books, readers, and loan records
- SQLite database integration

## Installation

1. Clone the repository.

2. Create a virtual environment:

   python -m venv .venv

3. Activate the virtual environment (Windows):

   .venv\Scripts\activate

4. Install dependencies:

   pip install -r requirements.txt

5. Configure the DJANGO_SECRET_KEY environment variable
   with your own generated secret key.

6. Apply database migrations:

   python manage.py migrate

7. Start the development server:

   python manage.py runserver

8. Open the application in your browser:

   http://127.0.0.1:8000/

## Database

The application uses SQLite to maintain reader information,
book records, and borrowing transactions.

## Author

Deep Halder
