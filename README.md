# ADS-B Military Aircraft Analyzer

This project fetches ADS-B (Automatic Dependent Surveillance-Broadcast) data, identifies military aircraft, and can log and report on these flights.

## Project Structure and Scripts

The project consists of the following main Python scripts:

*   **`adsb_fetcher.py`**:
    *   **Role**: Fetches live aircraft data from the `adsb.lol` API.
    *   It processes this data to identify aircraft that are likely military based on various criteria (e.g., 'mil' flag, operator keywords, aircraft type designators).
    *   It logs identified military aircraft to the `flight_log.db` database.
    *   **Note**: This script no longer uses internal mock data as a fallback; it focuses on live data. It does retain a set of specific test cases for verifying its `is_military_aircraft` logic.

*   **`db_manager.py`**:
    *   **Role**: Manages an SQLite database named `flight_log.db`.
    *   It is responsible for initializing the database schema and providing functions to log flight data.
    *   **Current Behavior**: If run directly (`python db_manager.py`), it will initialize the database and log a single dummy flight session (primarily for testing `db_manager.py` itself).

*   **`report_generator.py`**:
    *   **Role**: Generates an HTML summary report (`report.html`) based on the data stored in `flight_log.db`.
    *   **Current Behavior**: If run directly (`python report_generator.py`), it connects to `flight_log.db` and creates/overwrites `report.html` with several reports, including an overall military flight summary, costs by aircraft type, and a list of the top 20 most expensive logged military flights.

*   **`test_adsb_analyzer.py`**:
    *   **Role**: Contains unit tests for the project. (Further details about its content and how to run tests would require inspection of this file).

## Automated Workflow via GitHub Actions

This project utilizes GitHub Actions to automate the process of fetching flight data and generating reports.

-   **Daily Updates**: A workflow is scheduled to run daily (at midnight UTC). It can also be triggered by pushes to the `main` branch or manually.
-   **Data Fetching**: The action runs `adsb_fetcher.py` to fetch the latest military aircraft data from the live API, which is then logged into `flight_log.db`.
-   **Report Generation**: After fetching data, `report_generator.py` is executed to produce an updated `report.html` file based on the contents of `flight_log.db`.
-   **Automatic Commits**: The updated `flight_log.db` and `report.html` are automatically committed back to the repository.

You can find the latest generated report by viewing the `report.html` file in this repository. If GitHub Pages is enabled for this repository (serving from the `main` branch's root or `/docs` folder), the report may also be viewable directly at a URL like `https://<your-username>.github.io/<repository-name>/report.html`.

## How to Run Manually / For Development

While the primary operation is automated, you can run the scripts manually for development, testing, or immediate updates:

1.  **Ensure Dependencies (if any):**
    *   If the project had external Python dependencies listed in a `requirements.txt`, you would install them first (e.g., `pip install -r requirements.txt`). This project currently uses standard libraries.

2.  **Run the Data Fetcher and Logger:**
    *   Open your terminal or command prompt.
    *   Navigate to the project directory.
    *   Run the command: `python adsb_fetcher.py`
    *   **Behavior**:
        *   This script will first ensure the database (`flight_log.db`) and its tables are initialized.
        *   It will then attempt to fetch live aircraft data.
        *   Identified military aircraft will be printed to the console AND logged as flight sessions into the `flight_log.db` database.

3.  **Generate the HTML Report:**
    *   After `adsb_fetcher.py` has run, you can generate the report:
    *   In your terminal, run: `python report_generator.py`
    *   **Behavior**: This will read all logged flight sessions from `flight_log.db` and create/overwrite `report.html` with the summary reports. Open `report.html` in a web browser to view it.

*Running `python db_manager.py` directly is still possible for manually initializing the database or testing its functions, but it's not a required step for the main workflow.*

## Functionality Assessment

*   **Data Fetching, Identification, and Logging**: `adsb_fetcher.py` is functional in fetching live data, identifying military aircraft, and logging these aircraft to the `flight_log.db` database.
*   **Database Management**: `db_manager.py` is functional in creating, structuring, and saving data to the database.
*   **Reporting**: `report_generator.py` is functional in generating an HTML report (`report.html`) from the database content.
*   **Automation**: The process of data fetching, logging, and report generation is automated via GitHub Actions, ensuring the repository's `flight_log.db` and `report.html` are kept up-to-date.

## Testing

The project includes a test file: `test_adsb_analyzer.py`. Additionally, `adsb_fetcher.py` contains internal specific test cases to verify the `is_military_aircraft` classification logic.

To run tests defined in `test_adsb_analyzer.py` (assuming it uses a standard test framework like `unittest` or `pytest`):
1.  Ensure necessary test runners like `pytest` are installed (e.g., `pip install pytest`).
2.  Navigate to the project's root directory in your terminal.
3.  Run the command: `pytest` (or `python -m unittest discover` for `unittest`).

Executing these tests can help verify that individual functions and parts of the project are working as expected.
```
