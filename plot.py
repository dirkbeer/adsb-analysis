#!/usr/bin/env python3
import os
import subprocess
import sys
import pandas as pd
import numpy as np
from kneed import KneeLocator
import matplotlib.pyplot as plt
from scipy.stats import binom

# Read the CSV file
dat = pd.read_csv('output.csv', header=None)
dat.columns = ["aircraft_id", "distance", "present"]

# Bin the distances into intervals and calculate the proportion of presence
dat['distance_bin'] = pd.cut(dat['distance'], bins=np.arange(0, dat['distance'].max() + 10, 10), include_lowest=True, right=False)

# Calculate the proportion of presence in each bin
binned_data = dat.groupby('distance_bin', observed=False).agg(
    present_count=('present', 'sum'),
    total_count=('present', 'count')
).reset_index()
binned_data['proportion'] = binned_data['present_count'] / binned_data['total_count']

# Calculate the confidence intervals
def binom_confint(successes, trials):
    ci_low, ci_high = binom.interval(0.95, n=trials, p=successes/trials)
    return ci_low/trials, ci_high/trials

binned_data[['conf_low', 'conf_high']] = binned_data.apply(
    lambda row: binom_confint(row['present_count'], row['total_count']),
    axis=1, result_type='expand'
)

# Extract the far ranges from the bin name
def extract_upper_bound(interval):
    # Convert interval to string and remove parentheses
    interval_str = str(interval).strip('()[]')
    # Split the string by comma
    parts = interval_str.split(',')
    # Return the upper bound as float
    return float(parts[1].strip())

binned_data['distance'] = binned_data['distance_bin'].apply(extract_upper_bound)

# Find the knee in the curve
kn = KneeLocator(binned_data['distance'], binned_data['proportion'], S=2.0, curve='concave', direction='decreasing')
knee_point = (kn.knee, binned_data.loc[binned_data['distance'] == kn.knee, 'proportion'].values[0])

# Plot with confidence intervals
plt.figure(figsize=(10, 8))
plt.errorbar(binned_data['distance'], binned_data['proportion'], yerr=[binned_data['proportion'] - binned_data['conf_low'], binned_data['conf_high'] - binned_data['proportion']], fmt='o')
plt.scatter(*knee_point, color='red')
plt.annotate(f"Knee at {knee_point[0]} nautical miles", (knee_point[0], knee_point[1]))
plt.title("ADS-B Receiver Performance / Message Reliability")
plt.xlabel("Distance (nautical miles)")
plt.ylabel("Probability of Detection")
plt.ylim(0.7, 1.0)
plt.xlim(0.0, 300.0)
plt.grid(True)
plt.show()

# Save the plot
plt.savefig("receiver_performance.png")

