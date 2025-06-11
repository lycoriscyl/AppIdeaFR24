import sqlite3
import datetime
import os # To check for DB file existence

DB_FILE = "flight_log.db"

def get_db_connection():
    """Establishes and returns a SQLite connection."""
    if not os.path.exists(DB_FILE):
        print(f"Error: Database file '{DB_FILE}' not found. Please run adsb_fetcher.py to create it.")
        return None
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
    except sqlite3.Error as e:
        print(f"Error connecting to database {DB_FILE}: {e}")
    return conn

def format_timestamp(ts):
    """Converts a UNIX timestamp to a human-readable string."""
    if ts is None:
        return "N/A"
    try:
        return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    except TypeError:
        return "Invalid Timestamp"

def generate_report():
    """Generates and prints summary reports from the flight log database."""
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()

    print("\n--- Flight Log Report ---")

    # Query 1: Total Flights and Costs
    print("\n--- Overall Military Flight Summary ---")
    try:
        cursor.execute("SELECT COUNT(*), SUM(calculated_cost) FROM flight_sessions WHERE is_military_confirmed = 1;")
        result = cursor.fetchone()
        if result:
            total_flights, total_cost = result
            print(f"Total Logged Military Flights: {total_flights if total_flights is not None else 0}")
            print(f"Total Estimated Cost: ${total_cost if total_cost is not None else 0.00:,.2f}")
        else:
            print("No military flight data found.")
    except sqlite3.Error as e:
        print(f"Error executing Query 1 (Overall Summary): {e}")

    # Query 2: Costs by Aircraft Type
    print("\n--- Costs by Aircraft Type (Military) ---")
    try:
        cursor.execute("""
            SELECT aircraft_type_code, COUNT(*), SUM(calculated_cost)
            FROM flight_sessions
            WHERE is_military_confirmed = 1
            GROUP BY aircraft_type_code
            ORDER BY SUM(calculated_cost) DESC;
        """)
        results = cursor.fetchall()
        if results:
            print(f"{'Type':<10} | {'Flights':>7} | {'Total Cost':>15}")
            print("-" * 47)
            for row in results:
                type_code, count, cost = row
                print(f"{type_code if type_code else 'N/A':<10} | {count:>7} | ${cost if cost is not None else 0.00:>14,.2f}")
        else:
            print("No data found for costs by aircraft type.")
    except sqlite3.Error as e:
        print(f"Error executing Query 2 (Costs by Type): {e}")

    # Query 3: Top 20 Most Expensive Flights
    print("\n--- Top 20 Most Expensive Logged Military Flights ---")
    try:
        cursor.execute("""
            SELECT session_id, hex, aircraft_type_code, operator,
                   start_time, end_time, total_distance_nm, calculated_cost
            FROM flight_sessions
            WHERE is_military_confirmed = 1
            ORDER BY calculated_cost DESC
            LIMIT 20;
        """)
        results = cursor.fetchall()
        if results:
            print(f"{'ID':>3} | {'HEX':<8} | {'Type':<10} | {'Operator':<25} | {'Start Time':<19} | {'End Time':<19} | {'Distance (NM)':>13} | {'Cost':>15}")
            print("-" * 130) # Adjusted width
            for row in results:
                session_id, hex_val, type_code, operator, start_ts, end_ts, dist, cost = row
                start_dt = format_timestamp(start_ts)
                end_dt = format_timestamp(end_ts)
                print(f"{session_id:>3} | {hex_val:<8} | {type_code if type_code else 'N/A':<10} | {operator if operator else 'N/A':<25.25} | "
                      f"{start_dt:<19} | {end_dt:<19} | {dist if dist is not None else 0.00:>13.2f} | ${cost if cost is not None else 0.00:>14,.2f}")
        else:
            print("No flight data found for top expensive flights report.")
    except sqlite3.Error as e:
        print(f"Error executing Query 3 (Top Flights): {e}")

    if conn:
        conn.close()

if __name__ == "__main__":
    generate_report()
