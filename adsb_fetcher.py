import re
import requests
import json
from db_manager import log_flight_session, init_db

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
    init_db() # Initialize the database
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
                # Prepare flight_data for logging
                flight_data = {
                    'hex': aircraft.get('hex'),
                    'aircraft_type_code': aircraft.get('t'),
                    'operator': aircraft.get('op'),
                    'start_time': aircraft.get('ts'),
                    'end_time': aircraft.get('ts'), # Instantaneous data
                    'total_distance_nm': 0.0, # Not available
                    'calculated_cost': 0.0, # Not available
                    'is_military_confirmed': 1 # Changed to integer 1 for True
                }
                log_flight_session(flight_data)
            print(
                f"{i+1}. HEX: {aircraft.get('hex', 'N/A')}, "
                f"Type: {aircraft.get('t', 'N/A')}, Operator: {aircraft.get('op', 'N/A')}, "
                f"Lat: {aircraft.get('lat', 'N/A')}, Lon: {aircraft.get('lon', 'N/A')}, "
                f"Alt: {aircraft.get('alt_baro', 'N/A')}, GS: {aircraft.get('gs', 'N/A')}, "
                f"Category: {aircraft.get('category', 'N/A')}, Mil: {is_mil}"
            )

        print(f"\nTotal military aircraft detected from live feed: {military_aircraft_count}")
    # If no live data, a message is already printed. Script will then proceed to specific case verification.

    print("\n--- Specific Case Verification for is_military_aircraft function ---")
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
