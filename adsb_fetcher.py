import time
import copy
import csv
import math
import sys
from db_manager import init_db, log_flight_session # Import DB functions

# Global store for active military flights
ACTIVE_FLIGHTS = {}
FLIGHT_SESSION_TIMEOUT_SECONDS = 15 * 60  # 15 minutes
OPERATING_COSTS_DB = {} # To be populated by load_operating_costs

# Predefined list of military aircraft type codes (example)
MILITARY_AIRCRAFT_TYPES = ["F-16", "F-18", "F-22", "F-35A", "C-130H", "C-130J", "KC-135", "P-8A", "UH-60L", "E-3", "B-52H", "R135", "A400", "TY20", "A-10C", "MQ-9"]
MILITARY_OPERATOR_KEYWORDS = ["AIR FORCE", "NAVY", "ARMY", "GUARD", "COAST GUARD", "MARINES", "AFRICOM", "USAF", "ANG", "GAF", "PLAAF", "NATO"]

def load_operating_costs(filename="operating_costs.csv"):
    costs_db = {}
    try:
        with open(filename, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                aircraft_type = row.get("aircraft_type")
                cost_str = row.get("cost_per_hour")
                if aircraft_type and cost_str:
                    try:
                        costs_db[aircraft_type.upper()] = float(cost_str)
                    except ValueError:
                        print(f"Warning: Could not parse cost for {aircraft_type} as float: {cost_str}")
                else:
                    print(f"Warning: Missing aircraft_type or cost_per_hour in row: {row}")
        print(f"Successfully loaded operating costs for {len(costs_db)} aircraft types from {filename}")
    except FileNotFoundError:
        print(f"Error: Operating costs file '{filename}' not found. Cost calculations will be affected.")
    except Exception as e:
        print(f"Error loading operating costs from '{filename}': {e}")
    return costs_db

def haversine(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]: return 0.0
    R = 3440  # Nautical miles
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_total_distance(path_points):
    total_distance = 0.0
    if len(path_points) < 2: return 0.0
    for i in range(len(path_points) - 1):
        p1, p2 = path_points[i], path_points[i+1]
        total_distance += haversine(p1.get('lat'), p1.get('lon'), p2.get('lat'), p2.get('lon'))
    return total_distance

def get_mock_adsb_data(time_offset=0):
    base_ts = int(time.time()) + time_offset
    return [
        {"hex": "AE1234", "t": "F-16", "op": "USAF", "alt_baro": 25000 + time_offset*10, "gs": 500 + time_offset*2, "lat": 34.0 + time_offset*0.01, "lon": -118.0 + time_offset*0.01, "ts": base_ts - 120, "mil": True},
        {"hex": "AC5678", "t": "B738", "op": "Southwest Airlines", "alt_baro": 35000, "gs": 450, "lat": 36.0, "lon": -115.0, "ts": base_ts - 100, "mil": False},
        {"hex": "AE5F01", "t": "KC-135", "op": "168th ARW Alaska ANG", "alt_baro": 22000 - time_offset*10, "gs": 380, "lat": 64.8 - time_offset*0.01, "lon": -147.7 - time_offset*0.01, "ts": base_ts - 80, "mil": True},
        {"hex": "ADBF00", "t": "C-130J", "op": "US AIR FORCE", "alt_baro": 18000, "gs": 320, "lat": 33.0, "lon": -117.0, "ts": base_ts - 70, "mil": False},
        {"hex": "AE010A", "t": "P-8A", "op": "US NAVY", "alt_baro": 20000, "gs": 400, "lat": 32.7, "lon": -96.8, "ts": base_ts - 60, "mil": False},
        {"hex": "AE4C23", "t": "UH-60L", "op": "US ARMY", "alt_baro": 5000 + time_offset*5, "gs": 120 + time_offset, "lat": 34.7 + time_offset*0.005, "lon": -86.6 + time_offset*0.005, "ts": base_ts - 50, "mil": None},
        {"hex": "N12345", "t": "C172", "op": "CIVIL AIR PATROL", "alt_baro": 3000, "gs": 90, "lat": 35.0, "lon": -119.0, "ts": base_ts - 40, "mil": False},
        {"hex": "AE67F1", "t": "E-3", "op": "NATO", "alt_baro": 30000, "gs": 420, "lat": 52.0, "lon": 5.0, "ts": base_ts - 30, "mil": True},
        {"hex": "AE0477", "t": "B-52H", "op": "USAF", "alt_baro": 32000, "gs": 550, "lat": 47.0 + time_offset*0.02, "lon": -101.0 - time_offset*0.02, "ts": base_ts, "mil": True} if time_offset > 300 else None,
        {"hex": "AE5888", "t": "F-22", "op": "USAF ACC F22 DEMO", "alt_baro": 30000, "gs": 480, "lat": 38.8, "lon": -77.0, "ts": base_ts + 10 - (FLIGHT_SESSION_TIMEOUT_SECONDS if time_offset > 1000 else 0), "mil": True} if time_offset < 300 else None,
        {"hex": "AEFF00", "t": "UNKNOWN_MIL", "op": "MYSTERY SQUADRON", "alt_baro": 40000, "gs": 600, "lat": 40.0, "lon": -100.0, "ts": base_ts - 10, "mil": True}
    ]

def is_military_aircraft(aircraft_data):
    if aircraft_data is None: return False
    if aircraft_data.get("mil") is True: return True
    operator = aircraft_data.get("op", "").upper()
    if operator and any(keyword in operator for keyword in MILITARY_OPERATOR_KEYWORDS): return True
    aircraft_type = aircraft_data.get("t", "").upper()
    if aircraft_type and aircraft_type in MILITARY_AIRCRAFT_TYPES: return True
    return False

def check_and_process_ended_sessions(current_time):
    global OPERATING_COSTS_DB, ACTIVE_FLIGHTS
    print(f"\nChecking for ended sessions at time: {current_time} (Timeout: {FLIGHT_SESSION_TIMEOUT_SECONDS}s)")
    for hex_code in list(ACTIVE_FLIGHTS.keys()):
        flight_data = ACTIVE_FLIGHTS[hex_code]
        if current_time - flight_data['last_update_time'] > FLIGHT_SESSION_TIMEOUT_SECONDS:
            flight_duration_seconds = flight_data['last_update_time'] - flight_data['start_time']
            total_distance_nm = calculate_total_distance(flight_data['path'])

            aircraft_type_for_cost = flight_data['type'].upper()
            cost_per_hour = OPERATING_COSTS_DB.get(aircraft_type_for_cost)
            estimated_cost = 0.0
            cost_source_info = f"for {flight_data['type']}"

            if cost_per_hour is not None:
                estimated_cost = (flight_duration_seconds / 3600.0) * cost_per_hour
                cost_source_info = f"${cost_per_hour:,.2f}/hr for {flight_data['type']}"
            else:
                print(f"Warning: Operating cost not found for aircraft type '{flight_data['type']}'. Using $0.00/hr for cost estimation.")
                cost_source_info = f"unknown cost/hr for {flight_data['type']} (defaulted to $0.00)"

            print(f"\nFlight session ended for HEX={hex_code}:")
            print(f"  Type: {flight_data['type']}, Operator: {flight_data['operator']}")
            print(f"  Duration: {flight_duration_seconds / 60.0:.2f} minutes (Start: {flight_data['start_time']}, End: {flight_data['last_update_time']})")
            print(f"  Distance: {total_distance_nm:.2f} NM (Points: {len(flight_data['path'])})")
            print(f"  Estimated Cost: ${estimated_cost:,.2f} (based on {cost_source_info})")

            # Prepare data for logging
            session_log_data = {
                'hex': flight_data['hex'],
                'aircraft_type_code': flight_data['type'], # Assumes type in flight_data is the code
                'operator': flight_data['operator'],
                'start_time': flight_data['start_time'],
                'end_time': flight_data['last_update_time'],
                'total_distance_nm': total_distance_nm,
                'calculated_cost': estimated_cost,
                'is_military_confirmed': flight_data.get('is_military', True) # Default to True as it's processed as military
            }
            log_flight_session(session_log_data) # Log to SQLite database

            del ACTIVE_FLIGHTS[hex_code]

if __name__ == "__main__":
    OPERATING_COSTS_DB = load_operating_costs()
    if not OPERATING_COSTS_DB:
        print("Warning: Operating costs database is empty. Cost calculations will be zero.")

    init_db() # Initialize the database and tables

    current_simulated_time_offset = 0
    simulation_step_interval = 5 * 60  # 5 minutes
    total_simulation_steps = 5 # Reduced for quicker test runs if needed
    latest_timestamp_processed = int(time.time())

    print("\nStarting ADSB Data Processing Simulation...")
    print("-----------------------------------------")

    for i in range(total_simulation_steps):
        print(f"\n--- Simulation Step {i+1} (Time Offset: {current_simulated_time_offset // 60} mins) ---")
        mock_data = [data for data in get_mock_adsb_data(time_offset=current_simulated_time_offset) if data is not None]

        if not mock_data: print("No aircraft data in this fetch.")

        current_fetch_max_ts = 0
        for aircraft in mock_data:
            if aircraft.get("ts", 0) > latest_timestamp_processed: latest_timestamp_processed = aircraft.get("ts")
            if aircraft.get("ts",0) > current_fetch_max_ts: current_fetch_max_ts = aircraft.get("ts")

            if is_military_aircraft(aircraft):
                hex_code = aircraft.get("hex")
                aircraft_type = aircraft.get("t", "N/A")
                operator = aircraft.get("op", "N/A")
                lat = aircraft.get("lat")
                lon = aircraft.get("lon")
                alt_baro = aircraft.get("alt_baro", "N/A")
                gs = aircraft.get("gs", "N/A")
                timestamp = aircraft.get("ts")

                if not timestamp:
                    print(f"Skipping military aircraft {hex_code} due to missing timestamp.")
                    continue

                point = {"lat": lat, "lon": lon, "alt": alt_baro, "spd": gs, "ts": timestamp}

                if hex_code not in ACTIVE_FLIGHTS:
                    ACTIVE_FLIGHTS[hex_code] = {
                        "hex": hex_code, "type": aircraft_type, "operator": operator,
                        "start_time": timestamp, "last_update_time": timestamp,
                        "path": [point], "is_military": True
                    }
                    print(f"New military flight session started: HEX={hex_code}, Type={aircraft_type}, Operator='{operator}' at ts {timestamp}")
                else:
                    ACTIVE_FLIGHTS[hex_code]["path"].append(point)
                    ACTIVE_FLIGHTS[hex_code]["last_update_time"] = timestamp
                    print(f"Updating military flight session: HEX={hex_code}, Points={len(ACTIVE_FLIGHTS[hex_code]['path'])}, LastUpdate={timestamp}")

        effective_check_time = current_fetch_max_ts if current_fetch_max_ts > 0 else latest_timestamp_processed
        check_and_process_ended_sessions(current_time=effective_check_time)

        print("\nCurrent ACTIVE_FLIGHTS:")
        if ACTIVE_FLIGHTS:
            for h, f_data in ACTIVE_FLIGHTS.items():
                print(f"  HEX: {h}, Type: {f_data['type']}, Points: {len(f_data['path'])}, Last Update: {f_data['last_update_time']}")
        else:
            print("  No active military flights.")

        current_simulated_time_offset += simulation_step_interval
        time.sleep(0.05)

    print("\n-----------------------------------------")
    print("Simulation Finished.")
    # ... (rest of the printing logic for final state can be kept if desired)

    final_check_time = latest_timestamp_processed + FLIGHT_SESSION_TIMEOUT_SECONDS + 1
    print(f"\nPerforming a final session check at time: {final_check_time} to clear any remaining timed-out flights...")
    check_and_process_ended_sessions(current_time=final_check_time)
    print("\nFinal ACTIVE_FLIGHTS state after cleanup:")
    if ACTIVE_FLIGHTS:
        for h, f_data in ACTIVE_FLIGHTS.items(): # Should be empty if all timed out
            print(f"  HEX: {h}, Type: {f_data['type']}, Operator: {f_data['operator']}, Points: {len(f_data['path'])}, Start: {f_data['start_time']}, Last: {f_data['last_update_time']}")
    else:
        print("  No active military flights remaining.")
