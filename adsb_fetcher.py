import re
import requests
import json

# Predefined list of military aircraft type codes (example)
MILITARY_AIRCRAFT_TYPES = ["F16", "F18", "F22", "F35", "C130", "C17", "KC135", "P8", "UH60", "E3CF", "A400", "MRTT", "CC150", "HC144", "TYPHOON", "SNTNL", "UAV"]

# Keywords indicative of military operators
MILITARY_OPERATOR_KEYWORDS = [
    "AIR FORCE", "NAVY", "ARMY", "GUARD", "COAST GUARD", "MARINES",
    "DEFENCE", "MINISTRY OF DEFENCE", "LUFTWAFFE", "ARMÉE DE L'AIR", "NATO"
]

# Regex for common military abbreviations (ensures whole word match)
MILITARY_ABBREVIATIONS_REGEX = r"\b(USAF|USN|USMC|USCG|ANG|RAF|RCAF|GAF|FAF)\b"
# GAF = German Air Force, FAF = French Air Force (though full name is also in keywords)

def get_mock_adsb_data():
    """
    Returns a list of dictionaries, simulating flight data from an ADSBexchange API.
    """
    return [
        {"hex": "AE1234", "t": "F16", "op": "USAF", "alt_baro": 25000, "gs": 500, "lat": 34.0, "lon": -118.0, "ts": 1678886400, "mil": True},
        {"hex": "AC5678", "t": "B738", "op": "Southwest Airlines", "alt_baro": 35000, "gs": 450, "lat": 36.0, "lon": -115.0, "ts": 1678886420, "mil": False},
        {"hex": "AE5F01", "t": "KC135", "op": "168th ARW Alaska ANG", "alt_baro": 22000, "gs": 380, "lat": 64.8, "lon": -147.7, "ts": 1678886500, "mil": True},
        {"hex": "ADBF00", "t": "C17", "op": "US AIR FORCE", "alt_baro": 18000, "gs": 320, "lat": 33.0, "lon": -117.0, "ts": 1678886550, "mil": False},
        {"hex": "AE010A", "t": "P8", "op": "US NAVY", "alt_baro": 20000, "gs": 400, "lat": 32.7, "lon": -96.8, "ts": 1678886600, "mil": False},
        {"hex": "AE4C23", "t": "UH60", "op": "US ARMY", "alt_baro": 5000, "gs": 120, "lat": 34.7, "lon": -86.6, "ts": 1678886650, "mil": None},
        {"hex": "N12345", "t": "C172", "op": "CIVIL AIR PATROL", "alt_baro": 3000, "gs": 90, "lat": 35.0, "lon": -119.0, "ts": 1678886700, "mil": False},
        {"hex": "AE67F1", "t": "E3CF", "op": "NATO", "alt_baro": 30000, "gs": 420, "lat": 52.0, "lon": 5.0, "ts": 1678886750, "mil": True},
        {"hex": "43C2F2", "t": "A400", "op": "ROYAL AIR FORCE", "alt_baro": 15000, "gs": 300, "lat": 51.5, "lon": -0.1, "ts": 1678886800, "mil": None},
        {"hex": "7CF001", "t": "MRTT", "op": "LUFTWAFFE", "alt_baro": 28000, "gs": 430, "lat": 52.5, "lon": 13.4, "ts": 1678886850, "mil": True},
        {"hex": "AE20C1", "t": "C130", "op": "US MARINES", "alt_baro": 10000, "gs": 250, "lat": 32.8, "lon": -117.1, "ts": 1678886900, "mil": True},
        {"hex": "3EBA00", "t": "A332", "op": "Armée de l'Air", "alt_baro": 32000, "gs": 480, "lat": 48.8, "lon": 2.3, "ts": 1678886950, "mil": False}, # Note: A332 is civil type, op is military
        {"hex": "AE040F", "t": "HC144", "op": "US COAST GUARD", "alt_baro": 8000, "gs": 200, "lat": 25.8, "lon": -80.2, "ts": 1678887000, "mil": None},
        {"hex": "ZZZ123", "t": "DRONE", "op": "UNKNOWN", "alt_baro": 500, "gs": 50, "lat": 35.1, "lon": -118.5, "ts": 1678887050, "mil": False},
        {"hex": "MIL001", "t": "UAV", "op": "CLASSIFIED", "alt_baro": 12000, "gs": 150, "lat": 37.0, "lon": -116.0, "ts": 1678887100, "mil": True},
        {"hex": "CFC876", "t": "CC150", "op": "RCAF", "alt_baro": 33000, "gs": 460, "lat": 45.4, "lon": -75.7, "ts": 1678887150, "mil": None}
    ]

def fetch_live_adsb_data():
    """
    Fetches live ADSB data from the adsb.lol API.
    """
    api_url = "https://api.adsb.lol/v2/mil"
    aircraft_list = []
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        try:
            response_data = response.json()
            print(f"Fetched {len(response_data.get('ac', []))} aircraft from API.")
            # Iterate through aircraft objects and map fields
            for api_ac in response_data.get('ac', []):
                aircraft = {
                    'hex': api_ac.get('hex'),
                    't': api_ac.get('t'), # aircraft type from API
                    'op': api_ac.get('flight', api_ac.get('r', 'N/A')), # use 'flight' if available, else 'r', else 'N/A'
                    'alt_baro': api_ac.get('alt_baro'),
                    'gs': api_ac.get('gs'),
                    'lat': api_ac.get('lat'),
                    'lon': api_ac.get('lon'),
                    'ts': api_ac.get('seen', response_data.get('now')), # timestamp
                    'mil': api_ac.get('mil', True), # Assume True if 'mil' field is not present, as it's from /v2/mil endpoint
                    'category': api_ac.get('category'), # Store this as it might be useful
                    'squawk': api_ac.get('squawk'),
                    'messages': api_ac.get('messages'),
                    'seen_pos': api_ac.get('seen_pos'),
                    'track': api_ac.get('track'),
                }
                aircraft_list.append(aircraft)
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON response from API.")
            return []
        except Exception as e:
            print(f"An error occurred during JSON processing: {e}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not fetch data from API: {e}")
        return []
    return aircraft_list

def is_military_aircraft(aircraft_data):
    """
    Determines if an aircraft is military based on its data.
    Checks:
    - The 'mil' flag (if True).
    - Keywords in the 'op' (operator) field (case-insensitive).
    - Common military abbreviations in 'op' field.
    - Predefined list of military aircraft type codes 't' (case-insensitive).
    """
    if aircraft_data.get("mil") is True:
        return True

    operator = aircraft_data.get("op", "").upper() # Convert to uppercase for case-insensitive matching
    if operator:
        for keyword in MILITARY_OPERATOR_KEYWORDS:
            if keyword.upper() in operator: # Ensure keyword is also uppercase for comparison
                return True

        if re.search(MILITARY_ABBREVIATIONS_REGEX, operator):
             return True

    aircraft_type = aircraft_data.get("t", "").upper() # Convert to uppercase for case-insensitive matching
    if aircraft_type and aircraft_type in [t.upper() for t in MILITARY_AIRCRAFT_TYPES]: # Compare with uppercase types
        return True

    return False

if __name__ == "__main__":
    print("Fetching live aircraft data...")
    live_aircraft_data = fetch_live_adsb_data()

    if not live_aircraft_data:
        print("No live aircraft data received or an error occurred.")
    else:
        print(f"\n--- Live Aircraft Data (Total: {len(live_aircraft_data)}) ---")
        military_aircraft_count = 0
        for i, aircraft in enumerate(live_aircraft_data):
            is_mil = is_military_aircraft(aircraft)
            if is_mil:
                military_aircraft_count +=1
            print(
                f"{i+1}. HEX: {aircraft.get('hex', 'N/A')}, "
                f"Type: {aircraft.get('t', 'N/A')}, Operator: {aircraft.get('op', 'N/A')}, "
                f"Lat: {aircraft.get('lat', 'N/A')}, Lon: {aircraft.get('lon', 'N/A')}, "
                f"Alt: {aircraft.get('alt_baro', 'N/A')}, GS: {aircraft.get('gs', 'N/A')}, "
                f"Category: {aircraft.get('category', 'N/A')}, Mil: {is_mil}"
            )

        print(f"\nTotal military aircraft detected from live feed: {military_aircraft_count}")

    # Keep the existing mock data tests for is_military_aircraft function verification
    print("\n--- Running Mock Data Tests for is_military_aircraft function ---")
    mock_data = get_mock_adsb_data()
    military_aircraft_count_mock = 0

    print("--- Military Aircraft Detection Report (Mock Data) ---")
    for aircraft in mock_data:
        if is_military_aircraft(aircraft):
            military_aircraft_count_mock += 1
            # This detailed print can be verbose for mock data, consider summarizing
            # print(
            #     f"Military Aircraft Detected: HEX={aircraft.get('hex', 'N/A')}, "
            #     f"Type={aircraft.get('t', 'N/A')}, Operator={aircraft.get('op', 'N/A')}, "
            #     f"MilFlag={aircraft.get('mil', 'N/A')}"
            # )

    if military_aircraft_count_mock == 0:
        print("\nNo military aircraft detected in the mock data (is_military_aircraft test).")
    else:
        print(f"\nTotal military aircraft detected in mock data (is_military_aircraft test): {military_aircraft_count_mock}")

    # print("\n--- All Aircraft Data (Mock - for verification) ---")
    # expected_military_hex = [
    #     "AE1234", "AE5F01", "ADBF00", "AE010A", "AE4C23", "AE67F1",
    #     "43C2F2", "7CF001", "AE20C1", "3EBA00", "AE040F", "MIL001", "CFC876"
    # ]
    # for i, aircraft in enumerate(mock_data):
    #     classification = is_military_aircraft(aircraft)
    #     status_char = "M" if classification else "C"
    #     expected_char = "M" if aircraft.get('hex') in expected_military_hex else "C"
    #     correctness_indicator = "OK" if status_char == expected_char else "MISMATCH"
    #     print(
    #         f"{i+1}. HEX: {aircraft.get('hex')}, Type: {aircraft.get('t')}, Op: {aircraft.get('op')}, "
    #         f"Mil Flag: {aircraft.get('mil')}, Classified: {status_char}, Expected: {expected_char} -> {correctness_indicator}"
    #     )

    print("\n--- Specific Case Verification (Mock Data - True Positive & True Negative) ---")
    test_cases = [
        # Expected True
        {"name": "Mil Flag True", "data": {"hex": "AE1234", "t": "F16", "op": "USAF", "mil": True}, "expected": True},
        {"name": "Operator Keyword (AIR FORCE)", "data": {"hex": "ADBF00", "t": "C17", "op": "US AIR FORCE", "mil": False}, "expected": True},
        {"name": "Operator Keyword (NATO)", "data": {"hex": "AE67F3", "t": "AWACS", "op": "NATO AWACS Component", "mil": False}, "expected": True},
        {"name": "Operator Keyword (Armée de l'Air)", "data": {"hex": "3EBA00", "t": "A332", "op": "Armée de l'Air", "mil": False}, "expected": True},
        {"name": "Operator Abbreviation (RAF)", "data": {"hex": "XYZ789", "t": "TYPHOON", "op": "RAF LPCNT", "mil": None}, "expected": True},
        {"name": "Operator Abbreviation (ANG)", "data": {"hex": "AE5F01", "t": "KC135", "op": "168th ARW Alaska ANG", "mil": True}, "expected": True},
        {"name": "Aircraft Type (F22)", "data": {"hex": "AEBBCC", "t": "F22", "op": "Fighter Wing (Generic)", "mil": False}, "expected": True},
        {"name": "Mil=None, Op=US ARMY, Type=UH60", "data": {"hex": "AE4C23", "t": "UH60", "op": "US ARMY", "mil": None}, "expected": True},
        {"name": "Coast Guard, mil=None", "data": {"hex": "AE040F", "t": "HC144", "op": "US COAST GUARD", "mil": None}, "expected": True},
        {"name": "RCAF, mil=None", "data": {"hex": "CFC876", "t": "CC150", "op": "RCAF", "mil": None}, "expected": True},
        # Expected False
        {"name": "Standard Civilian", "data": {"hex": "AC5678", "t": "B738", "op": "Southwest Airlines", "mil": False}, "expected": False},
        {"name": "Civil Air Patrol", "data": {"hex": "N12345", "t": "C172", "op": "CIVIL AIR PATROL", "mil": False}, "expected": False},
        {"name": "Unknown Drone", "data": {"hex": "ZZZ123", "t": "DRONE", "op": "UNKNOWN", "mil": False}, "expected": False},
        {"name": "No explicit military indicators", "data": {"hex": "NOINFO", "t": "CESSNA", "op": "PRIVATE OWNER", "mil": None}, "expected": False},
        {"name": "Operator contains 'US' but not a mil abbrev", "data": {"hex": "USAIR", "t": "B747", "op": "US Airways", "mil": False}, "expected": False}
    ]

    all_tests_passed = True
    for case in test_cases:
        result = is_military_aircraft(case["data"])
        status = "PASSED" if result == case["expected"] else "FAILED"
        if result != case["expected"]:
            all_tests_passed = False
        print(f"Test '{case['name']}': Result={result}, Expected={case['expected']} -> {status}")
        if status == "FAILED":
            print(f"   Details: Data={case['data']}")
            if case["data"].get("mil") is True and not result: print("    Mil flag was True, should be True")
            if not case["data"].get("mil"):
                operator = case["data"].get("op", "").upper()
                ac_type = case["data"].get("t", "").upper()
                op_keywords_check = any(keyword.toUpperCase() in operator for keyword in MILITARY_OPERATOR_KEYWORDS)
                op_abbrev_check = re.search(MILITARY_ABBREVIATIONS_REGEX, operator)
                type_check = ac_type in [t.upper() for t in MILITARY_AIRCRAFT_TYPES]
                print(f"    Op: '{operator}', Type: '{ac_type}'")
                print(f"    OpKeywordMatch: {op_keywords_check}, OpAbbrevMatch: {bool(op_abbrev_check)}, TypeMatch: {type_check}")

    if all_tests_passed:
        print("\nAll specific mock data test cases passed successfully.")
    else:
        print("\nSome specific mock data test cases FAILED.")

    print("\nScript execution complete.")
