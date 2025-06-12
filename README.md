# ADS-B Military Aircraft Analyzer

This project fetches ADS-B (Automatic Dependent Surveillance-Broadcast) data, identifies military aircraft, and can log and report on these flights.

## Project Structure and Scripts

The project consists of the following main Python scripts:

*   **`adsb_fetcher.py`**:
    *   **Role**: Fetches live aircraft data from the `adsb.lol` API or uses mock data if the API is unavailable or for testing.
    *   It processes this data to identify aircraft that are likely military based on various criteria (e.g., 'mil' flag, operator keywords, aircraft type designators).
    *   **Current Behavior**: Prints the details of fetched aircraft and its military classification to the console. It also runs internal tests using mock data to verify its classification logic.
    *   **Note**: In its current state, this script *does not* save the fetched data to the database.

*   **`db_manager.py`**:
    *   **Role**: Manages an SQLite database named `flight_log.db`.
    *   It is responsible for initializing the database schema, including tables for `aircraft_types` and `flight_sessions`.
    *   It provides a function `log_flight_session()` to insert flight data into the database.
    *   **Current Behavior**: If run directly (`python db_manager.py`), it will initialize the database (creating `flight_log.db` if it doesn't exist) and log a single dummy flight session for testing purposes.

*   **`report_generator.py`**:
    *   **Role**: Generates summary reports based on the data stored in `flight_log.db`.
    *   **Current Behavior**: If run directly (`python report_generator.py`), it connects to `flight_log.db` and prints several reports, including:
        *   Overall military flight summary (total flights, total estimated costs).
        *   Costs broken down by aircraft type (military only).
        *   A list of the top 20 most expensive logged military flights.
    *   **Note**: The quality and content of these reports depend entirely on the data present in `flight_log.db`. If `adsb_fetcher.py` has not been modified to save data, these reports will only reflect dummy data (if `db_manager.py` was run) or be empty.

*   **`test_adsb_analyzer.py`**:
    *   **Role**: Contains unit tests for the project. (Further details about its content and how to run tests would require inspection of this file).

## How to Run the Project (Integrated Workflow)

With the recent changes, `adsb_fetcher.py` now automatically initializes the database and logs detected military aircraft.

1.  **Run the Data Fetcher and Logger:**
    *   Open your terminal or command prompt.
    *   Navigate to the project directory.
    *   Run the command: `python adsb_fetcher.py`
    *   **Behavior**:
        *   This script will first ensure the database (`flight_log.db`) and its tables are initialized (by calling functionality from `db_manager.py`).
        *   It will then attempt to fetch live aircraft data.
        *   Identified military aircraft will be printed to the console AND logged as flight sessions into the `flight_log.db` database.
        *   If live data fetching fails, it will process its internal mock data, and military aircraft from this mock set will also be logged (this part might be optional based on implementation).

2.  **Generate Reports:**
    *   After `adsb_fetcher.py` has run at least once (and successfully processed some data), you can generate reports.
    *   In your terminal, run: `python report_generator.py`
    *   **Behavior**: This will read all logged flight sessions from `flight_log.db` (including those just added by `adsb_fetcher.py`) and print summary reports to the console.

*Running `python db_manager.py` directly is still possible for manually initializing the database or testing its functions, but it's no longer a required first step for the main workflow.*

## Functionality Assessment

*   **Data Fetching, Identification, and Logging**: `adsb_fetcher.py` is functional in fetching data, identifying military aircraft, and **now logs these aircraft to the `flight_log.db` database.**
*   **Database Management**: `db_manager.py` is functional in creating, structuring, and saving data to the database, now primarily used by `adsb_fetcher.py`.
*   **Reporting**: `report_generator.py` is functional in generating reports from the database content, which now includes data captured from the live feed.

**Integrated Pipeline**: The project now functions as an integrated pipeline where fetched and identified military aircraft are automatically logged to the database, making them available for reporting via `report_generator.py`.

## Testing

The project includes a test file: `test_adsb_analyzer.py`.

This file is intended to house automated tests for the project's components. To run these tests, you would typically use a Python test runner like `pytest` or the built-in `unittest` module.

For example, if using `pytest`:
1.  Ensure `pytest` is installed (`pip install pytest`).
2.  Navigate to the project's root directory in your terminal.
3.  Run the command: `pytest`

Executing the tests can help verify that individual functions and parts of the project (like the aircraft identification logic or database operations) are working as expected, especially after making changes to the codebase.
```
