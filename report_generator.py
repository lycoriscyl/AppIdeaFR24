import sqlite3
import datetime
import os # To check for DB file existence

DB_FILE = "flight_log.db"

def get_db_connection():
    """Establishes and returns a SQLite connection."""
    if not os.path.exists(DB_FILE):
        # This message will go to console, HTML report will indicate DB not found
        print(f"Error: Database file '{DB_FILE}' not found. Please run adsb_fetcher.py to create it.")
        return None
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
    except sqlite3.Error as e:
        print(f"Error connecting to database {DB_FILE}: {e}") # Console message
    return conn

def format_timestamp(ts):
    """Converts a UNIX timestamp to a human-readable string."""
    if ts is None:
        return "N/A"
    try:
        return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    except TypeError: # Handles if ts is not a number or out of range
        return "Invalid Timestamp"
    except ValueError: # Handles if ts is out of valid range for fromtimestamp
        return "Invalid Timestamp Value"


def generate_report():
    """Generates an HTML summary report from the flight log database."""
    html_parts = []

    # HTML Boilerplate and CSS
    html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flight Log Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        table { border-collapse: collapse; width: 95%; margin: 20px auto; box-shadow: 0 2px 3px rgba(0,0,0,0.1); }
        th, td { border: 1px solid #ddd; text-align: left; padding: 10px; }
        th { background-color: #007bff; color: white; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        tr:hover { background-color: #f1f1f1; }
        h1 { text-align: center; color: #007bff; margin-bottom: 30px; }
        h2 { color: #0056b3; border-bottom: 2px solid #007bff; padding-bottom: 8px; margin-top: 30px;}
        .currency { text-align: right; }
        .numeric { text-align: right; }
        .text { text-align: left; }
        .container { background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .no-data { color: #777; font-style: italic; margin-left: 20px;}
    </style>
</head>
<body>
    <div class="container">
        <h1>ADS-B Military Flight Log Report</h1>
""")

    if not os.path.exists(DB_FILE):
        html_parts.append(f"<p>Error: Database file '{DB_FILE}' not found. Please run adsb_fetcher.py to create it and then re-run this report generator.</p>")
        html_parts.append("    </div>\n</body>\n</html>")
        final_html = "".join(html_parts)
        try:
            with open("report.html", "w", encoding="utf-8") as f:
                f.write(final_html)
            print(f"Generated report.html (database not found message).")
        except IOError as e:
            print(f"Error writing HTML report: {e}")
        return


    conn = get_db_connection()
    if conn is None:
        html_parts.append("<p>Error: Could not establish database connection. Report generation aborted.</p>")
        html_parts.append("    </div>\n</body>\n</html>")
        final_html = "".join(html_parts)
        try:
            with open("report.html", "w", encoding="utf-8") as f:
                f.write(final_html)
            print(f"Generated report.html (database connection error message).")
        except IOError as e:
            print(f"Error writing HTML report: {e}")
        return

    cursor = conn.cursor()

    # Query 1: Total Flights and Costs
    html_parts.append("<h2>Overall Military Flight Summary</h2>")
    try:
        cursor.execute("SELECT COUNT(*), SUM(calculated_cost) FROM flight_sessions WHERE is_military_confirmed = 1;")
        result = cursor.fetchone()
        if result and result[0] is not None and result[0] > 0 :
            total_flights, total_cost = result
            html_parts.append("<table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>")
            html_parts.append(f"<tr><td>Total Logged Military Flights</td><td class='numeric'>{total_flights}</td></tr>")
            html_parts.append(f"<tr><td>Total Estimated Cost</td><td class='currency'>${total_cost if total_cost is not None else 0.00:,.2f}</td></tr>")
            html_parts.append("</tbody></table>")
        else:
            html_parts.append("<p class='no-data'>No military flight data found for overall summary.</p>")
    except sqlite3.Error as e:
        html_parts.append(f"<p class='no-data'>Error executing Query 1 (Overall Summary): {e}</p>")

    # Query 2: Costs by Aircraft Type
    html_parts.append("<h2>Costs by Aircraft Type (Military)</h2>")
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
            html_parts.append("<table><thead><tr><th>Type</th><th>Flights</th><th>Total Cost</th></tr></thead><tbody>")
            for row in results:
                type_code, count, cost = row
                type_code_str = type_code if type_code else 'N/A'
                cost_val = cost if cost is not None else 0.00
                html_parts.append(f"<tr><td class='text'>{type_code_str}</td><td class='numeric'>{count}</td><td class='currency'>${cost_val:,.2f}</td></tr>")
            html_parts.append("</tbody></table>")
        else:
            html_parts.append("<p class='no-data'>No data found for costs by aircraft type.</p>")
    except sqlite3.Error as e:
        html_parts.append(f"<p class='no-data'>Error executing Query 2 (Costs by Type): {e}</p>")

    # Query 3: Top 20 Most Expensive Flights
    html_parts.append("<h2>Top 20 Most Expensive Logged Military Flights</h2>")
    try:
        cursor.execute("""
            SELECT session_id, hex, aircraft_type_code, operator,
                   start_time, end_time, total_distance_nm, calculated_cost
            FROM flight_sessions
            WHERE is_military_confirmed = 1 AND calculated_cost > 0
            ORDER BY calculated_cost DESC
            LIMIT 20;
        """)
        results = cursor.fetchall()
        if results:
            html_parts.append("<table><thead><tr><th>ID</th><th>HEX</th><th>Type</th><th>Operator</th><th>Start Time</th><th>End Time</th><th>Distance (NM)</th><th>Cost</th></tr></thead><tbody>")
            for row in results:
                session_id, hex_val, type_code, operator, start_ts, end_ts, dist, cost = row
                start_dt = format_timestamp(start_ts)
                end_dt = format_timestamp(end_ts)
                type_code_str = type_code if type_code else 'N/A'
                operator_str = operator if operator else 'N/A'
                dist_val = dist if dist is not None else 0.00
                cost_val = cost if cost is not None else 0.00 # Should not be None due to WHERE clause
                html_parts.append(f"<tr><td class='numeric'>{session_id}</td><td class='text'>{hex_val}</td><td class='text'>{type_code_str}</td><td class='text'>{operator_str}</td>"
                                  f"<td class='text'>{start_dt}</td><td class='text'>{end_dt}</td><td class='numeric'>{dist_val:.2f}</td><td class='currency'>${cost_val:,.2f}</td></tr>")
            html_parts.append("</tbody></table>")
        else:
            html_parts.append("<p class='no-data'>No flight data found for top expensive flights report (with cost > 0).</p>")
    except sqlite3.Error as e:
        html_parts.append(f"<p class='no-data'>Error executing Query 3 (Top Flights): {e}</p>")

    html_parts.append("    </div>\n</body>\n</html>") # Close container and HTML

    final_html = "".join(html_parts)
    try:
        with open("report.html", "w", encoding="utf-8") as f:
            f.write(final_html)
        print("Successfully generated HTML report: report.html")
    except IOError as e:
        print(f"Error writing HTML report to file: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    generate_report()
```
