# adsb-analysis

ADS-B Receiver Performance - Message Reliability at Distance

This looks at how reliably you receive ADS-B messages over a range of distance from your location. Reliability drops off with distance, but the better your system, the farther out it will receive reliably.

The reliability metric used is probability of detection P(D) of an aircraft's message in the current measurement interval, given that that the aircraft's message was received in the previous interval:

$$
P(D_{i+1} \mid D_i)
$$

The intervals used are those in the tar1090 data, specified by `INTERVAL` in `/etc/default/tar1090`, `INTERVAL=8` seconds by default. The analysis runs on all the data stored by tar1090. The amount of data stored by tar1090 is specified by `HISTORY_SIZE` in `/etc/default/tar1090`, `HISTORY_SIZE=450` (1 hour) by default (450 snapshots * 8 seconds per snapshot / 3600 seconds per hour = 1 hour).

To get a good dataset for this analysis, you should have tar1090 collect more data. For example, try setting `HISTORY_SIZE=1800` in `/etc/default/tar1090` (4 hours), and running the analysis around 2pm to capture the 10ma-2pm midday air traffic.

The plot below is an example using 4 hours of data. It shows roughly the pattern expected in theory:

* The P(D) stays high (90%-100%) at low ranges where the signal is well above the detection threshold of the receiver. 
* At the range where the signal gets near the detection threshold, P(D) starts dropping rapidly.
* Where this transition happens (the "knee") is a good indication of sensitivity and performance of the receiver/amplifier/filter/antenna system.

![image](https://github.com/dirkbeer/adsb-analysis/assets/6425332/c886a056-473b-4d5b-b506-6a182b4e70b9)


**Setup** (run again to update to latest)
```bash
curl -sSL https://raw.githubusercontent.com/dirkbeer/adsb-analysis/main/setup.sh | bash
```

**Running the analysis**
```bash
./run_analysis.sh
```

**Command line options**

Don't use these routinely unless you know what you are doing and have a specific reason.

```
usage: analyze.py [-h] [--dynamic-limits] [--use-all] [--figure-filename FIGURE_FILENAME]

Script to analyze ADS-B Receiver Performance

optional arguments:
  -h, --help                                                Show this help message and exit
  --dynamic-limits, -dl                                     Use dynamic limits to ensure all data is visible
  --use-all, -a                                             Calculate statistics on range bins even if there is insufficient data for valid statistics
  --figure-filename FIGURE_FILENAME, -ffn FIGURE_FILENAME   Filename for the saved plot
```
