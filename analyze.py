#!/usr/bin/env python3
import sys

def is_running_in_venv():
    return sys.prefix != sys.base_prefix

if is_running_in_venv():
    print("Running in a virtual environment.")
    import gzip
    import json
    import glob
    import math
    import datetime
    import re
    import argparse
    import pandas as pd
    import numpy as np
    from kneed import KneeLocator
    import matplotlib.pyplot as plt
    from scipy.stats import binom
    from scipy.optimize import OptimizeWarning
    import warnings
else:
    print("Not running in the virtual environment. Run \"source venv/bin/activate\" first. ")
    sys.exit(1)

# Global variables from the first script
data_dir = '/run/tar1090'
config_file_path = '/etc/default/readsb'

def extract_lat_lon_from_config(config_file_path):
    with open(config_file_path, 'r') as file:
        config_content = file.read()

    lat_lon_pattern = r"--lat\s+([+-]?\d+\.\d+)\s+--lon\s+([+-]?\d+\.\d+)"
    match = re.search(lat_lon_pattern, config_content)

    if match:
        lat = float(match.group(1))
        lon = float(match.group(2))
        return lat, lon
    else:
        print("Latitude and longitude not found in the readsb config file.\n")
        print("Set your location using \"sudo readsb-set-location <lat> <lon>\" and try again.\n")
        exit(1)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Radius of the Earth in kilometers
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1000  # Distance in meters

def extract_data(file_content, latitude_home, longitude_home):
    json_data = json.loads(file_content)
    extracted_data = []
    for entry in json_data.get("files", []):
        time = entry.get("now") * 1000
        for aircraft in entry.get("aircraft", []):
            aircraft_id = aircraft[0]
            latitude, longitude = aircraft[4] if len(aircraft) > 4 else None, aircraft[5] if len(aircraft) > 5 else None
            if latitude is not None and longitude is not None:
                distance = haversine(latitude, longitude, latitude_home, longitude_home)
                extracted_data.append([aircraft_id, time, latitude, longitude, distance])
    return extracted_data

# Class definition from the first script
class Data:
    def __init__(self, row):
        self.aircraft_id, self.time, self.latitude, self.longitude, self.distance = row
        self.distance /= 1852  # Convert to nautical miles
        self.datetime = datetime.datetime.utcfromtimestamp(self.time / 1000)

def get_knee_point(binned_data):
    # Input validation
    if not isinstance(binned_data, pd.DataFrame):
        print("Errors encountered in knee point calculation, no knee point will be plotted")
        return (None, None)

    required_columns = ['distance', 'proportion']
    if not all(column in binned_data.columns for column in required_columns):
        print("Errors encountered in knee point calculation, no knee point will be plotted")
        return (None, None)

    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            kn = KneeLocator(binned_data['distance'], binned_data['proportion'], 
                             curve='concave', direction='decreasing',
                             interp_method='piecewise', online=False)

            if w:
                print("Errors encountered in knee point calculation, no knee point will be plotted")
                return (None, None)

            knee_point = (kn.knee, binned_data.loc[binned_data['distance'] == kn.knee, 'proportion'].values[0]) if kn.knee is not None else None
            return knee_point

    except (OptimizeWarning, Exception):
        print("Errors encountered in knee point calculation, no knee point will be plotted")
        return (None, None)

def binom_confint(successes, trials):
    if trials == 0:
        return np.nan, np.nan
    ci_low, ci_high = binom.interval(0.95, n=trials, p=successes/trials)
    return ci_low/trials, ci_high/trials

def extract_upper_bound(interval):
    interval_str = str(interval).strip('()[]')
    parts = interval_str.split(',')
    return float(parts[1].strip())

# Integrated main function
def main():

    # Process command line arguments
    parser = argparse.ArgumentParser(description="Script to analyze ADS-B Receiver Performance")
    parser.add_argument('--dynamic-limits', '-dl', action='store_true', help='Use dynamic limits to ensure all data is visible')
    parser.add_argument('--use-all', '-a', action='store_true', help='Calculate statistics on range bins even if there is insufficient data for valid statistics')
    parser.add_argument('--figure-filename', '-ffn', type=str, default='receiver_performance.png', help='Filename for the saved plot')
    args = parser.parse_args()
    
    # Extract latitude and longitude from config
    latitude_home, longitude_home = extract_lat_lon_from_config(config_file_path)
    print(f"Home location from {config_file_path}: {latitude_home}, {longitude_home}")

    # Process and extract data
    file_pattern = f"{data_dir}/chunk_*.gz"
    filenames = glob.glob(file_pattern)
    all_data = []

    for filename in filenames:
        try:
            with gzip.open(filename, 'rt') as f:
                file_content = f.read()
                extracted_data = extract_data(file_content, latitude_home, longitude_home)
                all_data.extend([Data(row) for row in extracted_data])
        except FileNotFoundError:
            print(f"File not found: {filename}")
            continue
        except OSError as e:
            print(f"OS error occurred with file {filename}: {e}")
            continue

    # After processing all data, calculate the earliest and latest dates
    if all_data:
        earliest_date = min(d.datetime for d in all_data)
        latest_date = max(d.datetime for d in all_data)
        # Calculate the time difference
        time_difference = latest_date - earliest_date
        total_seconds = time_difference.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)

        # Format the date range string with hours and minutes
        date_range_str = (f"{earliest_date.strftime('%Y-%m-%d %H:%M')} to "
                          f"{latest_date.strftime('%Y-%m-%d %H:%M')} "
                          f"({hours} hours, {minutes} minutes)")
    else:
        date_range_str = "No data available"

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
    
    dat = pd.DataFrame(output_data, columns=["aircraft_id", "distance", "present"])

    # Bin the distances into intervals and calculate the proportion of presence
    dat['distance_bin'] = pd.cut(dat['distance'], bins=np.arange(0, dat['distance'].max() + 10, 10), include_lowest=True, right=False)

    # Calculate the proportion of presence in each bin
    binned_data = dat.groupby('distance_bin', observed=True).agg(
        present_count=('present', 'sum'),
        total_count=('present', 'count')
    ).reset_index()
    binned_data['proportion'] = binned_data['present_count'] / binned_data['total_count']

    # Filter the data to include only rows where total_count > 30 to ensure valid statistics
    if not args.use_all:
        pre_filter_bin_count = len(binned_data)
        binned_data = binned_data[binned_data['total_count'] >= 30]
        post_filter_bin_count = len(binned_data)
        filtered_bins = pre_filter_bin_count - post_filter_bin_count 
        if filtered_bins > 1:        # It's normal for the last bin to have too few messages, don't bother the user if there is only one bin filtered
            print(f"Filtering {filtered_bins} range bins because they had to few messages for valid statistics. Set --use-all on the command line to override.")

    # Calculate the confidence intervals
    binned_data[['conf_low', 'conf_high']] = binned_data.apply(
        lambda row: binom_confint(row['present_count'], row['total_count']),
        axis=1, result_type='expand'
    )
    
    # Extract the far ranges from the bin name
    binned_data['distance'] = binned_data['distance_bin'].apply(extract_upper_bound)

    # Plot with confidence intervals using filtered data
    plt.figure(figsize=(10, 8))
    plt.errorbar(binned_data['distance'], binned_data['proportion'], 
                 yerr=[binned_data['proportion'] - binned_data['conf_low'], 
                       binned_data['conf_high'] - binned_data['proportion']], fmt='o')

    knee_point = get_knee_point(binned_data)
    if knee_point[1] is not None:
        plt.scatter(*knee_point, color='red')
        plt.annotate(f"Knee at {knee_point[0]} nautical miles", (knee_point[0]+2, knee_point[1]))

    plt.title("ADS-B Receiver Performance / Message Reliability")
    plt.xlabel("Distance (nautical miles)")
    plt.ylabel("Probability of Detection")
    if not args.dynamic_limits:
        plt.ylim(0.7, 1.0)
        plt.xlim(0.0, 300.0)
    plt.grid(True)
    plt.show()
    plt.text(0.05, 0.01, f"Data Range: {date_range_str}", fontsize=8, ha='left', transform=plt.gcf().transFigure)
    plt.text(0.95, 0.01, "https://github.com/dirkbeer/adsb-analysis", fontsize=8, ha='right', transform=plt.gcf().transFigure)

    # Save the plot
    plt.savefig(args.figure_filename)

if __name__ == "__main__":
    main()
