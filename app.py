import os
import pymysql
from pymysql.cursors import DictCursor
from flask import Flask, render_template, g, current_app

app = Flask(__name__)

# Configure your MySQL connection parameters
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'secure_root_password')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'fp_sbd')

def get_db():
    """Opens a new database connection for the current app context."""
    if 'db' not in g:
        g.db = pymysql.connect(
            host=current_app.config['MYSQL_HOST'],
            user=current_app.config['MYSQL_USER'],
            password=current_app.config['MYSQL_PASSWORD'],
            database=current_app.config['MYSQL_DB'],
            cursorclass=DictCursor
        )
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Closes the MySQL connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Reads schema.sql and initializes the database tables."""
    print("Checking database tables...")
    # Open a direct connection outside of the request context
    connection = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    
    try:
        with connection.cursor() as cursor:
            # Read the raw SQL file
            with open('schema.sql', 'r') as f:
                sql_script = f.read()
            
            # Split the script into individual queries by semicolon
            sql_commands = sql_script.split(';')
            
            for command in sql_commands:
                # Execute only if the command is not an empty string
                if command.strip():
                    cursor.execute(command)
                    
        connection.commit()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        connection.close()

@app.route('/')
def home():
    # Example route logic
    return render_template('home.html')

if __name__ == '__main__':
    print("  _    _ _____  ____   _____   _______ ____  ______ ______ _      ")
    print(" | |  | |  __ \|  _ \ / ____| |__   __/ __ \|  ____|  ____| |     ")
    print(" | |  | | |__) | |_) | |  __     | | | |  | | |__  | |__  | |     ")
    print(" | |  | |  ___/|  _ <| | |_ |    | | | |  | |  __| |  __| | |     ")
    print(" | |__| | |    | |_) | |__| |    | | | |__| | |____| |    | |____ ")
    print("  \____/|_|    |____/ \_____|    |_|  \____/|______|_|    |______|")
    print("                                                                  ")
    print("                                                                  ")

    # Initialize the database right before starting the server
    print("=" * 15)
    print("Initializing database...")
    print("=" * 15)
    init_db()

    print("Starting Flask server...")
    app.run(debug=True)
