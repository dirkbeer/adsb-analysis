#!/usr/bin/env python3

import gzip
import json
import glob
import math
import datetime
import re


data_dir = '/run/tar1090'
config_file_path = '/etc/default/readsb'

def extract_lat_lon_from_config(config_file_path):
    with open(config_file_path, 'r') as file:
        config_content = file.read()

    # Regular expression pattern to find latitude and longitude
    lat_lon_pattern = r"--lat\s+([+-]?\d+\.\d+)\s+--lon\s+([+-]?\d+\.\d+)"

    # Search for the pattern in the configuration content
    match = re.search(lat_lon_pattern, config_content)

    if match:
        lat = float(match.group(1))
        lon = float(match.group(2))
        return lat, lon
    else:
        return None, None

# get the home lat and lon from the readsb config file
latitude_home, longitude_home = extract_lat_lon_from_config(config_file_path)
print(f"Home location from {config_file_path}: {latitude_home}, {longitude_home}")

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Radius of the Earth in kilometers
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1000  # Distance in meters

def extract_data(file_content):
    json_data = json.loads(file_content)
    extracted_data = []
    for entry in json_data.get("files", []):
        time = entry.get("now")
        for aircraft in entry.get("aircraft", []):
            aircraft_id = aircraft[0]
            latitude, longitude = aircraft[4] if len(aircraft) > 4 else None, aircraft[5] if len(aircraft) > 5 else None
            if latitude is not None and longitude is not None:
                distance = haversine(latitude, longitude, latitude_home, longitude_home)
                extracted_data.append([aircraft_id, time, latitude, longitude, distance])
    return extracted_data

# Functions and class from Script B
class Data:
    def __init__(self, row):
        self.aircraft_id, self.time, self.latitude, self.longitude, self.distance = row
        self.distance /= 1852  # Convert to nautical miles
        self.datetime = datetime.datetime.utcfromtimestamp(self.time / 1000)

def main():
    file_pattern = f"{data_dir}/chunk_*.gz"
    filenames = glob.glob(file_pattern)
    all_data = []

    # Extract and process data
    for filename in filenames:
        try:
            with gzip.open(filename, 'rt') as f:
                file_content = f.read()
                extracted_data = extract_data(file_content)
                all_data.extend([Data(row) for row in extracted_data])
        except FileNotFoundError:
            print(f"File not found: {filename}")
            continue  # Skip to the next filename
        except OSError as e:  # Handles other I/O errors such as a bad gzip file
            print(f"OS error occurred with file {filename}: {e}")
            continue

    times = {d.time for d in all_data}
    data_per_time_and_aircraft = {}
    for d in all_data:
        if d.time not in data_per_time_and_aircraft:
            data_per_time_and_aircraft[d.time] = {}
        data_per_time_and_aircraft[d.time][d.aircraft_id] = d

    output_data = []
    sorted_times = sorted(times)
    for i, current_time in enumerate(sorted_times):
        next_time = sorted_times[i + 1] if i + 1 < len(sorted_times) else None
        for aircraft_id, d in data_per_time_and_aircraft[current_time].items():
            present_in_next = next_time is not None and aircraft_id in data_per_time_and_aircraft[next_time]
            output_data.append((aircraft_id, d.distance, int(present_in_next)))

    # Write final data to a file
    with open("output.csv", "w") as output_file:
        for entry in output_data:
            output_file.write(f"{entry[0]}, {entry[1]}, {entry[2]}\n")

if __name__ == "__main__":
    main()