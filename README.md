# adsb-analysis

***ADS-B Receiver Performance - Maximum Reliable Range***

This looks at how reliably you receive ADS-B messages over a range of distance from your location. Reliability drops off with distance, but the better your system, the farther out it will receive reliably. The plots show a "knee" that is the maximum reliable range.

<p align="center">
  <img src="https://github.com/dirkbeer/adsb-analysis/assets/6425332/cb3200c7-edf2-4bf1-9e10-c1176069f025" alt="knee plot">
</p>

**Setup the code** (run again to update to latest)
```bash
curl -sSL https://raw.githubusercontent.com/dirkbeer/adsb-analysis/main/setup.sh | bash
```

**Run the analysis**
```bash
~/adsb-analysis/run_analysis.sh
```

<p align="center">
  <img src="https://github.com/dirkbeer/adsb-analysis/assets/6425332/893a9c18-ef02-4adf-a811-46254d177576" alt="output">
</p>

&nbsp;&nbsp;&nbsp;Ctrl-click the link in the resulting output to see the plot.

**Requirements**

&nbsp;&nbsp;&nbsp;&nbsp;readsb (included in the wingbits.com install)
<br><br>

---

***Theory***

The reliability metric used is probability of detection P(D) of an aircraft's message in the current 8-second measurement interval, given that that the aircraft's message was received in the previous interval:

$$
P(D_{i+1} \mid D_i)
$$

This method doesn't need to know ground truth of which airplanes are out there and when they transmitted because it takes advantage of the fact that aircraft repeat the transmission every few seconds. If you don't hear the aircraft again in a few seconds, it's probably because reception at that range is unreliable, not because the it disappeared (thanks to @thegristleking for that explanation). 

***Usage***

If you're optimizing your system for collecting quality data, graph1090's Peak Range or Avg Max Range are misleading because those don't tell you how far out you *reliably* pick up messages. The maximum reliable "knee" range does.

The optimization procedure I'm currently using is: 1) set the gain (e.g. using autogain `for i in {0..30}; do sudo autogain1090; sleep 120; done &`), 2) wait an hour for some data and then check the knee range with adsb-analysis 3) modify my setup and repeat.

The plot above is an example using just 15 minutes of data. It shows roughly the pattern expected in theory:

* The P(D) stays high (90%-100%) at low ranges where the signal is well above the detection threshold of the receiver. 
* At the range where the signal gets near the detection threshold, P(D) starts dropping rapidly.
* Where this transition happens (the "knee") is the maximum reliable range of the receiver/amplifier/filter/antenna system.
