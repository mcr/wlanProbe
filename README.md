
This MicroPython (https://micropython.org) code runs on a ESP32 and
scan available WLANs, connects to a WLAN and disconnect from a WLAN. To
prevent event spamming each event is separated by a little sleep. All
scans and other events generate data, which is send to a configured
MQTT server.
Has been developed with MicroPython 20190529-v1.11 on Olimex ESP32-POE
and Pycom Wipy 3.0 hardware.
This version still contains debug output and garbage collection
experiments.

