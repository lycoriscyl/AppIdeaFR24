import sqlite3
import time
import os # Added for test cleanup

DB_FILE = "flight_log.db"

def get_db_connection():
    """Returns a SQLite connection object to the database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
    except sqlite3.Error as e:
        print(f"Error connecting to database {DB_FILE}: {e}")
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    if conn is None:
        print("Failed to get database connection. Database initialization aborted.")
        return

    try:
        cursor = conn.cursor()

        # Create aircraft_types table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aircraft_types (
                type_code TEXT PRIMARY KEY,
                description TEXT
            )
        """)

        # Create flight_sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flight_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                hex TEXT NOT NULL,
                aircraft_type_code TEXT,
                operator TEXT,
                start_time INTEGER,
                end_time INTEGER,
                total_distance_nm REAL,
                calculated_cost REAL,
                is_military_confirmed INTEGER,
                FOREIGN KEY (aircraft_type_code) REFERENCES aircraft_types(type_code)
            )
        """)

        conn.commit()
        print(f"Database {DB_FILE} initialized successfully. Tables created or already exist.")

    except sqlite3.Error as e:
        print(f"Error during database initialization: {e}")
    finally:
        if conn:
            conn.close()

def log_flight_session(flight_data):
    """
    Logs a flight session to the database.
    flight_data is a dictionary with all necessary fields.
    """
    conn = get_db_connection()
    if conn is None:
        print("Failed to get database connection. Flight session logging aborted.")
        return

    sql = """
        INSERT INTO flight_sessions (
            hex, aircraft_type_code, operator, start_time, end_time,
            total_distance_nm, calculated_cost, is_military_confirmed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    try:
        cursor = conn.cursor()
        cursor.execute(sql, (
            flight_data.get('hex'),
            flight_data.get('aircraft_type_code'),
            flight_data.get('operator'),
            flight_data.get('start_time'),
            flight_data.get('end_time'),
            flight_data.get('total_distance_nm'),
            flight_data.get('calculated_cost'),
            int(flight_data.get('is_military_confirmed', 0)) # Convert boolean to int
        ))
        conn.commit()
        print(f"Successfully logged flight session for HEX: {flight_data.get('hex')} to database.")
    except sqlite3.Error as e:
        print(f"Error logging flight session for HEX {flight_data.get('hex')}: {e}")
    except Exception as ex:
        print(f"An unexpected error occurred while logging flight session for HEX {flight_data.get('hex')}: {ex}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Example usage: Initialize DB and log a dummy session
    print("Running db_manager.py directly for testing...")
    init_db()

    # Example: Add an aircraft type (optional here, could be managed separately)
    # conn = get_db_connection()
    # if conn:
    #     try:
    #         cursor = conn.cursor()
    #         cursor.execute("INSERT OR IGNORE INTO aircraft_types (type_code, description) VALUES (?, ?)", ("F-16", "Fighting Falcon"))
    #         conn.commit()
    #         print("Added/Ensured F-16 in aircraft_types")
    #     except sqlite3.Error as e:
    #         print(f"Error adding F-16 type: {e}")
    #     finally:
    #         conn.close()

    dummy_flight = {
        'hex': 'AE1234_TEST',
        'aircraft_type_code': 'F-16', # Ensure this type exists in aircraft_types if FK is enforced strictly and type not added.
        'operator': 'Test Air Force',
        'start_time': int(time.time()) - 3600,
        'end_time': int(time.time()),
        'total_distance_nm': 500.75,
        'calculated_cost': 12500.50,
        'is_military_confirmed': True
    }
    # To make this test runnable without adsb_fetcher creating the type first,
    # we might need to ensure F-16 is in aircraft_types or handle it.
    # For now, let's assume F-16 is added or FK constraint is not immediate issue for this test.
    # A better test would be to add the type first.

    # Let's add the type explicitly for the test to be robust
    conn_test = get_db_connection()
    if conn_test:
        try:
            cursor = conn_test.cursor()
            cursor.execute("INSERT OR IGNORE INTO aircraft_types (type_code, description) VALUES (?, ?)",
                           (dummy_flight['aircraft_type_code'], "Test Description"))
            conn_test.commit()
            print(f"Ensured aircraft type {dummy_flight['aircraft_type_code']} exists for test.")
        except sqlite3.Error as e:
            print(f"Error ensuring aircraft type for test: {e}")
        finally:
            conn_test.close()

    log_flight_session(dummy_flight)
    print("db_manager.py test finished.")
