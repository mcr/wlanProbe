'''
This MicroPython (https://micropython.org) code runs on a ESP32 and
scan available WLANs, connects to a WLAN and disconnect from a WLAN. To
prevent event spamming each event is separated by a little sleep.
Has been developed with MicroPython 20190529-v1.11 on Olimex ESP32-POE
and Pycom Wipy 3.0 hardware.
'''
import network
import time
import ubinascii
import sys

CONFIG = {
    "SSID": "TheInternet",
    "WlanSecret": "",
    "eventTimeDiff": 4,
    }

EVENTCOUNTS = {
    "Connect": 0,
    "Disconnect": 0,
    "WlanScan": 0,
    "WlanStatus": 0,
    }


def connectWLAN(inNic, inSSID, inWlanSecret):
    # connect to WLAN access point
    print("## Try to connect to SSID", inSSID)
    try:
        EVENTCOUNTS["Connect"] += 1
        print("## Localtime for Connect", time.localtime())
        inNic.connect(inSSID, inWlanSecret)
        time.sleep_ms(500)
        if inNic.isconnected():
            print("## Connected to", inSSID)
    except Exception as e:
        print("## Exception while connecting to WLAN")
        sys.print_exception(e)


def disconnectWLAN(inNic):
    # disconnect from WLAN
    print("## Going to disconnect from WLAN")
    try:
        EVENTCOUNTS["Disconnect"] += 1
        print("## Localtime for Disconnect", time.localtime())
        inNic.disconnect()
        time.sleep_ms(500)
        if inNic.isconnected():
            print("## WLAN has been disconnected")
    except Exception as e:
        print("## WLAN disconnect failed")
        sys.print_exception(e)


def statusWLAN(inNic):
    # get status of WLAN
    try:
        EVENTCOUNTS["WlanStatus"] += 1
        print("## Localtime for WLAN Status", time.localtime())
        wlanIfconfig = inNic.ifconfig()
        wlanRSSI = inNic.status("rssi")
        print("\n## Configuration of WLAN interface")
        print("IP-address:", wlanIfconfig[0],
              "Netmask:", wlanIfconfig[1],
              "Router:", wlanIfconfig[2],
              "DNS:", wlanIfconfig[3],
              "RSSI:", wlanRSSI,
              )
        print("\n")
    except Exception as e:
        print("## Exception while connecting to WLAN")
        sys.print_exception(e)


def scanWLAN(inNic):
    availableAuthModes = {
        0: "open",
        1: "WEP",
        2: "WPA-PSK",
        3: "WPA2-PSK",
        4: "WPA/WPA2-PSK",
        }
    try:
        EVENTCOUNTS["WlanScan"] += 1
        # interface has to be in disconnected mode for a scan
        disconnectWLAN(inNic)
        # get available WLAN networks
        print("## Localtime for WLAN scan", time.localtime())
        wlanScan = inNic.scan()
        print("\n## Found WLAN Networks")
        for foundWLAN in wlanScan:
            ssid = foundWLAN[0].decode("UTF-8")
            bssid = ubinascii.hexlify(foundWLAN[1]).decode("UTF-8")
            authModeInt = foundWLAN[4]
            if authModeInt in availableAuthModes:
                authMode = availableAuthModes[authModeInt]
            else:
                authMode = "Unkown mode " + str(authModeInt)
            print("SSID:", ssid,
                  "BSSID:", bssid,
                  "Channel:", foundWLAN[2],
                  "RSSI:", foundWLAN[3],
                  "Authmode:", authMode,
                  "Hidden:", foundWLAN[5],
                  )
        print("\n")
    except Exception as e:
        print("## Exception while connecting to WLAN")
        sys.print_exception(e)


def eventScheduler(inEventTimer, inEventTimeDiff):
    # wait a certain time to keep activity low
    nextEventTime = inEventTimer + inEventTimeDiff
    print("## Localtime for Event", time.localtime())
    print("## Next event at", nextEventTime)
    while nextEventTime > time.time():
        time.sleep_ms(100)
    return nextEventTime


def main():
    # does some WLAN actions to leave a trail of events
    nic = network.WLAN(network.STA_IF)
    eventTimer = time.time()
    print("## Getting started")
    nic.active(True)
    while True:
            if not nic.isconnected():
                scanWLAN(nic)
                eventTimer = eventScheduler(eventTimer,
                                            CONFIG["eventTimeDiff"],
                                            )
                connectWLAN(nic,
                            CONFIG["SSID"],
                            CONFIG["WlanSecret"],
                            )
                eventTimer = eventScheduler(eventTimer,
                                            CONFIG["eventTimeDiff"],
                                            )
            else:
                statusWLAN(nic)
                eventTimer = eventScheduler(eventTimer,
                                            CONFIG["eventTimeDiff"],
                                            )
                disconnectWLAN(nic)
                eventTimer = eventScheduler(eventTimer,
                                            CONFIG["eventTimeDiff"],
                                            )
            print("Event Counters")
            for i in EVENTCOUNTS.keys():
                print(i, EVENTCOUNTS[i])


if __name__ == "__main__":
    main()
