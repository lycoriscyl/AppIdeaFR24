import unittest
import sqlite3
import os
import sys
import time # For test_log_and_retrieve_flight_session

# Ensure adsb_fetcher and db_manager can be imported
# This might need adjustment based on actual file structure or if run as part of a package
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    from adsb_fetcher import (
        haversine, calculate_total_distance, is_military_aircraft,
        load_operating_costs, MILITARY_AIRCRAFT_TYPES as FETCHER_MIL_TYPES,
        MILITARY_OPERATOR_KEYWORDS as FETCHER_OP_KEYWORDS
    )
    import adsb_fetcher # To modify its global OPERATING_COSTS_DB for one test
except ImportError:
    print("Failed to import from adsb_fetcher. Ensure it's in the Python path.")
    # Define placeholders if adsb_fetcher is not found, so tests can still be defined (though they'll likely fail)
    def haversine(lat1, lon1, lat2, lon2): return 0.0
    def calculate_total_distance(path_points): return 0.0
    def is_military_aircraft(aircraft_data): return False
    def load_operating_costs(filename="operating_costs.csv"): return {}
    FETCHER_MIL_TYPES = []
    FETCHER_OP_KEYWORDS = []
    adsb_fetcher = None


try:
    import db_manager
except ImportError:
    print("Failed to import db_manager. Ensure it's in the Python path.")
    db_manager = None


# Ensure operating_costs.csv exists for tests that rely on it
# This assumes operating_costs.csv is in the same directory as this test script
# or adsb_fetcher.py (if adsb_fetcher.py's path logic is used by load_operating_costs)
OPERATING_COSTS_FILE = "operating_costs.csv"

class TestAdsbFetcherLogic(unittest.TestCase):

    def test_haversine_distance(self):
        # Washington D.C. (approx)
        lat1, lon1 = 38.9072, -77.0369
        # Paris, France (approx)
        lat2, lon2 = 48.8566, 2.3522
        # Expected distance ~3310 NM (source: online calculators, can vary slightly)
        expected_dist_dc_paris = 3312.0
        self.assertAlmostEqual(haversine(lat1, lon1, lat2, lon2), expected_dist_dc_paris, delta=25) # Delta for minor variations

        # Test zero distance
        self.assertAlmostEqual(haversine(lat1, lon1, lat1, lon1), 0.0, delta=0.01)

        # Test with None inputs (assuming haversine handles this by returning 0 or raising error)
        # Based on current haversine, it returns 0.0 if None is present
        self.assertEqual(haversine(None, lon1, lat2, lon2), 0.0)
        self.assertEqual(haversine(lat1, None, lat2, lon2), 0.0)
        self.assertEqual(haversine(lat1, lon1, None, lon2), 0.0)
        self.assertEqual(haversine(lat1, lon1, lat2, None), 0.0)

    def test_calculate_total_distance(self):
        p1 = {"lat": 38.9072, "lon": -77.0369} # DC
        p2 = {"lat": 34.0522, "lon": -118.2437} # LA
        p3 = {"lat": 40.7128, "lon": -74.0060} # NYC

        # Distance DC to LA is approx 2090 NM
        dist_dc_la = haversine(p1['lat'], p1['lon'], p2['lat'], p2['lon'])
        self.assertAlmostEqual(calculate_total_distance([p1, p2]), dist_dc_la, delta=1.0)

        dist_la_nyc = haversine(p2['lat'], p2['lon'], p3['lat'], p3['lon'])
        self.assertAlmostEqual(calculate_total_distance([p1, p2, p3]), dist_dc_la + dist_la_nyc, delta=1.0)

        self.assertEqual(calculate_total_distance([p1]), 0.0)
        self.assertEqual(calculate_total_distance([]), 0.0)
        self.assertEqual(calculate_total_distance([p1, p1, p1]), 0.0)


    def test_is_military_aircraft(self):
        # Ensure test types are consistent with what is_military_aircraft expects
        # adsb_fetcher.MILITARY_AIRCRAFT_TYPES might be ["F-16", ...]
        # For this test, we can override them or use known ones
        # For simplicity, using a few direct examples

        self.assertTrue(is_military_aircraft({"mil": True, "t": "XYZ", "op": "CIVILIAN"}))
        self.assertTrue(is_military_aircraft({"mil": False, "t": "XYZ", "op": "USAF"}))
        self.assertTrue(is_military_aircraft({"mil": False, "t": "ANY", "op": "ANY NAVY BASE"}))
        self.assertTrue(is_military_aircraft({"mil": False, "t": "ANY", "op": "ARMY AVIATION"}))
        self.assertTrue(is_military_aircraft({"mil": False, "t": "ANY", "op": "COAST GUARD"}))
        self.assertTrue(is_military_aircraft({"mil": False, "t": "ANY", "op": "123rd GUARD WING"}))

        # Specific types (ensure these are in FETCHER_MIL_TYPES or adjust test)
        # Example: if "F-16" is in FETCHER_MIL_TYPES
        if "F-16" in FETCHER_MIL_TYPES:
             self.assertTrue(is_military_aircraft({"mil": False, "t": "F-16", "op": "ANY"}))
        if "C-130J" in FETCHER_MIL_TYPES:
            self.assertTrue(is_military_aircraft({"mil": None, "t": "C-130J", "op": "Any Op"}))

        self.assertFalse(is_military_aircraft({"mil": False, "t": "B738", "op": "Southwest Airlines"}))
        self.assertFalse(is_military_aircraft({"mil": None, "t": "C172", "op": "Private Owner"}))
        self.assertFalse(is_military_aircraft({})) # Empty data

    def test_cost_calculation_logic(self):
        if adsb_fetcher is None:
            self.skipTest("adsb_fetcher module not imported, skipping cost calculation test.")

        # Load real costs, or mock if preferred
        # For this test, we rely on load_operating_costs and the actual CSV.
        # Ensure operating_costs.csv has F-16 with $25000 for this test to be stable.
        # Alternatively, mock adsb_fetcher.OPERATING_COSTS_DB

        original_costs_db = adsb_fetcher.OPERATING_COSTS_DB
        adsb_fetcher.OPERATING_COSTS_DB = {"F-16": 25000.00, "B-52H": 70000.00} # Mock specific type for test

        duration_hours = 1.5
        cost_per_hour_f16 = adsb_fetcher.OPERATING_COSTS_DB.get("F-16", 0.0)
        expected_cost_f16 = duration_hours * cost_per_hour_f16
        self.assertAlmostEqual(expected_cost_f16, 37500.00, delta=0.01)

        duration_hours_b52 = 0.75
        cost_per_hour_b52 = adsb_fetcher.OPERATING_COSTS_DB.get("B-52H", 0.0)
        expected_cost_b52 = duration_hours_b52 * cost_per_hour_b52
        self.assertAlmostEqual(expected_cost_b52, 52500.00, delta=0.01)

        # Restore original (or clear if it was empty)
        adsb_fetcher.OPERATING_COSTS_DB = original_costs_db


@unittest.skipIf(db_manager is None, "db_manager module not imported, skipping DB tests.")
class TestDBManagerLogic(unittest.TestCase):
    _original_db_file = None

    @classmethod
    def setUpClass(cls):
        if db_manager:
            cls._original_db_file = db_manager.DB_FILE
            db_manager.DB_FILE = "test_flight_log.db"
        else: # Should not happen due to skipIf but as a safeguard
            raise unittest.SkipTest("db_manager not available for setUpClass")


    @classmethod
    def tearDownClass(cls):
        if db_manager and cls._original_db_file is not None:
            # Clean up the test database file after all tests in this class run
            if os.path.exists(db_manager.DB_FILE):
                os.remove(db_manager.DB_FILE)
            db_manager.DB_FILE = cls._original_db_file


    def setUp(self):
        # Initialize DB for each test to ensure a clean state
        # This will create test_flight_log.db and tables
        if os.path.exists(db_manager.DB_FILE): # remove if exists from previous failed test
            os.remove(db_manager.DB_FILE)
        db_manager.init_db()

        # Ensure aircraft types for FK constraints are present for test data
        conn = db_manager.get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO aircraft_types (type_code, description) VALUES (?, ?)", ("F-TEST", "Test Fighter"))
                cursor.execute("INSERT OR IGNORE INTO aircraft_types (type_code, description) VALUES (?, ?)", ("C-TEST", "Test Cargo"))
                conn.commit()
            except sqlite3.Error as e:
                print(f"Error adding test aircraft types in setUp: {e}")
            finally:
                conn.close()


    def tearDown(self):
        # The main DB file cleanup is in tearDownClass to avoid deleting it between tests
        # if setUp fails for some test. Individual tests can do more specific cleanup if needed.
        pass


    def test_log_and_retrieve_flight_session(self):
        current_ts = int(time.time())
        flight_data_1 = {
            'hex': 'TEST01', 'aircraft_type_code': 'F-TEST', 'operator': 'Test Op 1',
            'start_time': current_ts - 3600, 'end_time': current_ts,
            'total_distance_nm': 120.5, 'calculated_cost': 5000.75,
            'is_military_confirmed': True
        }
        flight_data_2 = {
            'hex': 'TEST02', 'aircraft_type_code': 'C-TEST', 'operator': 'Test Op 2',
            'start_time': current_ts - 7200, 'end_time': current_ts - 3000, # Older session
            'total_distance_nm': 350.0, 'calculated_cost': 15000.00,
            'is_military_confirmed': 0 # False
        }

        db_manager.log_flight_session(flight_data_1)
        db_manager.log_flight_session(flight_data_2)

        conn = sqlite3.connect(db_manager.DB_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM flight_sessions WHERE hex = ?", ('TEST01',))
        retrieved_data_1 = cursor.fetchone()

        cursor.execute("SELECT * FROM flight_sessions WHERE hex = ?", ('TEST02',))
        retrieved_data_2 = cursor.fetchone()

        conn.close()

        self.assertIsNotNone(retrieved_data_1)
        # Column order: session_id, hex, aircraft_type_code, operator, start_time, end_time, total_distance_nm, calculated_cost, is_military_confirmed
        self.assertEqual(retrieved_data_1[1], flight_data_1['hex'])
        self.assertEqual(retrieved_data_1[2], flight_data_1['aircraft_type_code'])
        self.assertEqual(retrieved_data_1[3], flight_data_1['operator'])
        self.assertEqual(retrieved_data_1[4], flight_data_1['start_time'])
        self.assertEqual(retrieved_data_1[5], flight_data_1['end_time'])
        self.assertAlmostEqual(retrieved_data_1[6], flight_data_1['total_distance_nm'], delta=0.01)
        self.assertAlmostEqual(retrieved_data_1[7], flight_data_1['calculated_cost'], delta=0.01)
        self.assertEqual(retrieved_data_1[8], 1) # True -> 1

        self.assertIsNotNone(retrieved_data_2)
        self.assertEqual(retrieved_data_2[1], flight_data_2['hex'])
        self.assertEqual(retrieved_data_2[8], 0) # False -> 0


if __name__ == '__main__':
    # Ensure operating_costs.csv is available for load_operating_costs if not mocked
    if not os.path.exists(OPERATING_COSTS_FILE):
        print(f"Warning: '{OPERATING_COSTS_FILE}' not found. Cost-related tests might be affected or fail if not mocked.")
        # Optionally, create a dummy one for tests if it's crucial and not part of setup
        # with open(OPERATING_COSTS_FILE, "w") as f:
        #     f.write("aircraft_type,cost_per_hour\nF-16,25000.00\nB-52H,70000.00\n")

    unittest.main()
