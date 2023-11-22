# adsb-analysis

***ADS-B Receiver Performance - Maximum Reliable Range***

This looks at how reliably you receive ADS-B messages over a range of distance from your location. Reliability drops off with distance, but the better your system, the farther out it will receive reliably. The plots show a *maximum reliable range*.

<p align="center">
  <img src="https://github.com/dirkbeer/adsb-analysis/assets/6425332/cd5fda49-56d0-46bf-a54a-e45f0b2ca8b6" alt="knee plot">
</p>


**Setup the code** (run again to update to latest but note that it will overwrite any customizations)
```bash
curl -sSL https://raw.githubusercontent.com/dirkbeer/adsb-analysis/main/setup.sh | bash
```

**Run the analysis**
```bash
~/adsb-analysis/run_analysis.sh
```

<p align="center">
  <img src="https://github.com/dirkbeer/adsb-analysis/assets/6425332/1dd67298-f0e4-4b5c-8e66-7c268334efc2" alt="output">
</p>



**Requirements**

&nbsp;&nbsp;&nbsp;&nbsp;readsb (included in the wingbits.com install)
<br><br>

---

***Usage***

The optimization procedure I'm currently using is: 

1) set the gain to make sure it's as high as possible without overloading the receiver (e.g. using autogain `for i in {0..30}; do sudo autogain1090; sleep 120; done &`),
2) delete the previous tar1090 data `sudo rm /run/tar1090/*`,
3) wait some time for data (for me ~ 1 hour is sufficient) and then check the maximum reliable "knee" range with run-analysis.sh,
4) modify my setup and repeat.

The plot above is an example using 2 hours of data. It shows roughly the pattern expected in theory:

* The reliability stays high (90%-100%) at low ranges where the signal is well above the detection threshold of the receiver. 
* At the range where the signal gets near the detection threshold, reliability starts dropping rapidly.
* Where this transition happens (the "knee") is the *maximum reliable range* of the receiver/amplifier/filter/antenna system.
<br>

***Theory***

The reliability metric used is probability of detection P(D) of an aircraft's message in the current 8-second measurement interval, given that that the aircraft's message was received in the previous interval:

$$
P(D_{i+1} \mid D_i)
$$

This method doesn't need to know ground truth of which airplanes are out there and when they transmitted. It takes advantage of the fact that aircraft repeat the transmission every few seconds. 

If you don't hear the aircraft again in a few seconds, it's probably because reception at that range is unreliable, not because it disappeared (thanks to @thegristleking for that clear way of explaining it). 

*Maximum reliable range* is better than many graph1090 metrics if you want to optimize for lots of quality data:
* graph1090's *Peak Range* and *Avg Max Range* are misleading because they tell you where you can occasionally get lucky. *Maximum reliable range* tells you how far out you can receive complete quality data.
* graph1090's *Message Rate* and *Aircraft Seen/Tracked* are misleading because they fluctuate by the minute depending on time of day and flight schedules. The *maximum reliable range* is stable so you can be sure changes where due to your setup.


