'''
This MicroPython (https://micropython.org) code runs on a ESP32 and
scan available WLANs, connects to a WLAN and disconnect from a WLAN. To
prevent event spamming each event is separated by a little sleep. All
scans and other events generate data, which is send to a configured
MQTT server.
Has been developed with MicroPython 20190529-v1.11 on Olimex ESP32-POE
and Pycom Wipy 3.0 hardware.
This version still contains debug output and garbage collection
experiments.
'''
import gc
import hashlib
import json
import machine
import micropython
import network
import ntptime
import sys
import socket
import time
import ubinascii

from umqtt.robust import MQTTClient
from random import randint

UNIQ_ID = ubinascii.hexlify(machine.unique_id()).decode("UTF-8")

PLATFORM = sys.platform

CONFIG = {
    "connectTerm": 121,
    "debug": False,
    "eventTimeDiff": 1,
    "httpRepeat": 10,
    "httpSleepMS": 100,
    "httpURL": "http://10.128.128.1/20kb",
    "ntpBetween2Runs": 1903,
    "maximumRandomSecondsDelay": 11,
    "mqttArea": "StationA",
    "mqttBroker": "10.128.128.1",
    "mqttClientUniqueId": "wlanProbe_" + PLATFORM + "_" + UNIQ_ID,
    "mqttGroup": "wlanProbe",
    "mqttIdentifiers": ["mqttArea", "mqttClientUniqueId", "mqttGroup"],
    "mqttPassword": "ljseoifrj98324jsdj8932u",
    "mqttReceivedMax": 5,
    "mqttSSL": True,
    "mqttConfigTopic": "wlanProbe/Config",
    "mqttMeasureTopic": "wlanProbe/Measurement",
    "mqttUser": "wlanprobe",
    "wlanSecret": "sehfikowheuirh8923",
    "wlanSsid": "TheInternet",
    }

'''
Contains previous connection state to differ between disconnection on
purpose and by network disruption.
'''
PREVCONNECTED = False

MESSAGE_TYPES = {
    "connect": "Connect",
    "deviceStart": "DeviceStart",
    "disconnect": "Disconnect",
    "mqttErrorMessage": "MQTTErrorMessage",
    "mqttCollectStatus": "MQTTCollectStatus",
    "systemStatus": "SystemStatus",
    "wlanScan": "WlanScan",
    "wlanStatus": "WlanStatus",
    }

MQTTHASH = ["aykicWafEemLeokLocgo"]

MQTTRECEIVED = []

MQTTSTATS = {
    "acceptedMsgs": 0,
    "droppedMsgs": 0,
    "badMsgs": 0,
    "goodMsgs": 0,
    "receivedMsgs": 0,
    }

LIST_MESSAGE_TYPES = [
                      MESSAGE_TYPES["connect"],
                      MESSAGE_TYPES["disconnect"],
                      MESSAGE_TYPES["wlanStatus"],
                      MESSAGE_TYPES["systemStatus"],
                      ]


def checkState(inCheckFuncBool,
               inCheckFuncArgs="NotUsed",
               inDelay=220,
               inDelayRange=10,
               ioPatienceMultiplier=2,
               inMaximumPatience=20,
               ):
    checkedState = False
    delayLowerLimit = inDelay - inDelayRange
    delayUpperLimit = inDelay + inDelayRange
    if delayLowerLimit < 10:
        delayLowerLimit = 1
    if delayUpperLimit < delayLowerLimit:
        delayUpperLimit = 1 + delayLowerLimit
    randomDelay = randint(delayLowerLimit, delayUpperLimit)
    while ioPatienceMultiplier < inMaximumPatience:
        time.sleep_ms(randomDelay * ioPatienceMultiplier)
        ioPatienceMultiplier = ioPatienceMultiplier * ioPatienceMultiplier
        checkBool = inCheckFuncBool(inCheckFuncArgs)
        if checkBool:
            checkedState = True
            ioPatienceMultiplier = 9999
    # return Bool
    return checkedState


def connectCondition(inNic):
    # return Bool
    return inNic.isconnected()


def connectionMessage(inConnectData, inMessageSuccess, inMessageFailure,):
    outConnectData = []
    if inConnectData:
        print("##", inMessageSuccess)
        outConnectData.append("Success")
        outConnectData.append(inMessageSuccess)
    else:
        print("##", inMessageFailure)
        outConnectData.append(inMessageFailure)
    printDebug("Disconnect Output", outConnectData)
    # return List
    return outConnectData


def connectedSchedule(
        inNic,
        ioWlanData,
        ioConnectTime,
        ioEventTimer,
        ioMqttCounter,
        outNtpResult,
        ioNtpLastSuccess,
        ):
    '''
    When connected this code collects details of the connection and
    sends MQTT messages of the results.
    The HTTP measurements results are going to be collected in the
    Apache, not here.
    '''
    systemData = statusSystem()
    generatedMessage = generateMessageList(
                            time.time(),
                            0,
                            CONFIG["mqttClientUniqueId"],
                            MESSAGE_TYPES["systemStatus"],
                            systemData,
                            )
    mqttCollectData = mqttCollectMessages()
    generatedMessage = generateMessageList(
                            time.time(),
                            0,
                            CONFIG["mqttClientUniqueId"],
                            MESSAGE_TYPES["mqttCollectStatus"],
                            mqttCollectData,
                            )
    ioWlanData.append(generatedMessage)
    statusData = statusWLAN(inNic)
    generatedMessage = generateMessageList(
                            time.time(),
                            0,
                            CONFIG["mqttClientUniqueId"],
                            MESSAGE_TYPES["wlanStatus"],
                            statusData,
                            )
    ioWlanData.append(generatedMessage)
    ioEventTimer = eventScheduler(ioEventTimer,)
    timeDiff, outNtpResult, ioNtpLastSuccess = setLocalTime(ioNtpLastSuccess)
    ioMqttCounter = mqttCommit(ioMqttCounter,
                               CONFIG["mqttBroker"],
                               CONFIG["mqttMeasureTopic"],
                               CONFIG["mqttClientUniqueId"],
                               ioWlanData)
    ioEventTimer = eventScheduler(ioEventTimer,)
    printDebug("ioConnectTime", ioConnectTime)
    randomDelay = randint(0, CONFIG["maximumRandomSecondsDelay"])
    printDebug("randomDelay", randomDelay)
    secondsSinceLastConnect = (time.time() -
                               ioConnectTime -
                               randomDelay
                               )
    httpMeasurement()
    if secondsSinceLastConnect > CONFIG["connectTerm"]:
        disconnectData = disconnectWLAN(inNic)
        printDebug("Disconnect output in main()", disconnectData)
        generatedMessage = generateMessageList(
                                time.time(),
                                0,
                                CONFIG["mqttClientUniqueId"],
                                MESSAGE_TYPES["disconnect"],
                                disconnectData,
                                )
        ioWlanData.append(generatedMessage)
        ioEventTimer = eventScheduler(ioEventTimer,)
        printDebug("wlanData", ioWlanData)
        printDebug("connectTime", ioConnectTime)
        printDebug("eventTimer", ioEventTimer)
        printDebug("mqttCounter", ioMqttCounter)
    return (ioWlanData,
            ioConnectTime,
            ioEventTimer,
            ioMqttCounter,
            outNtpResult,
            ioNtpLastSuccess
            )


def connectWLAN(inNic, inSSID, inWlanSecret):
    global PREVCONNECTED
    # connect to WLAN access point
    print("## Try to connect to SSID", inSSID)
    inNic.connect(inSSID, inWlanSecret)
    connectData = checkState(connectCondition, inNic)
    if PREVCONNECTED:
        successMsg = "Restored failed connect to SSID " + CONFIG["wlanSsid"]
        failedMsg = "Still no connection with SSID " + CONFIG["wlanSsid"]
    else:
        successMsg = "Device connected to SSID " + CONFIG["wlanSsid"]
        failedMsg = "Connection to SSID " + CONFIG["wlanSsid"] + " failed."
    outConnectData = connectionMessage(
                        connectData,
                        successMsg,
                        failedMsg,
                        )
    if connectData:
        PREVCONNECTED = True
    outConnectTime = time.time()
    printDebug("Connect Output", outConnectData)
    return outConnectData, outConnectTime


def disconnectCondition(inNic):
    # return Bool
    return not inNic.isconnected()


def disconnectedSchedule(inNic, ioWlanData, ioConnectTime, ioEventTimer):
    '''
    WLAN can only be scanned, when the device is disconnected. This
    code scans and generates a message for when the device ist
    connected again.
    '''
    scanData = scanWLAN(inNic)
    generatedMessage = generateMessageList(
                            time.time(),
                            0,
                            CONFIG["mqttClientUniqueId"],
                            MESSAGE_TYPES["wlanScan"],
                            scanData,
                            )
    # Combine a list of lists
    ioWlanData = ioWlanData + generatedMessage
    ioEventTimer = eventScheduler(ioEventTimer,)
    connectData, tmpConnectTime = connectWLAN(inNic,
                                              CONFIG["wlanSsid"],
                                              CONFIG["wlanSecret"])
    printDebug("Connect output in main()", connectData)
    if connectData[0] == "Success":
        ioConnectTime = tmpConnectTime
    generatedMessage = generateMessageList(
                            time.time(),
                            0,
                            CONFIG["mqttClientUniqueId"],
                            MESSAGE_TYPES["connect"],
                            connectData,
                            )
    ioWlanData.append(generatedMessage)
    ioEventTimer = eventScheduler(ioEventTimer,)
    return ioWlanData, ioConnectTime, ioEventTimer


def disconnectWLAN(inNic):
    global PREVCONNECTED
    # disconnect from WLAN
    print("## Going to disconnect from WLAN")
    inNic.disconnect()
    connectData = checkState(disconnectCondition, inNic)
    if PREVCONNECTED:
        outConnectData = connectionMessage(
                            connectData,
                            "WLAN was successfully disconnected.",
                            "WLAN failed to disconnect.",
                            )
    else:
        outConnectData = connectionMessage(
                            connectData,
                            "Still disconnected from WLAN.",
                            "Disconnected WLAN failed to disconnect!?",
                            )
    if connectData:
        PREVCONNECTED = False
    return outConnectData


def eventScheduler(inEventTimer,
                   inEventTimeDiff=CONFIG["eventTimeDiff"],
                   ):
    # wait a certain time to keep activity low
    randomDelay = randint(2, 2 + CONFIG["maximumRandomSecondsDelay"])
    outNextEventTime = inEventTimer + inEventTimeDiff + randomDelay
    print("## Next event after", outNextEventTime)
    printDebug("nextEventTime", outNextEventTime)
    now = time.time()
    printDebug("now", now)
    while outNextEventTime > now:
        time.sleep(2)
        now = time.time()
    print("## Sleep for next event has ended at", time.time())
    return outNextEventTime


def garbageCollectList(inList):
    index = 1
    lengthList = len(inList)
    freeMem = gc.mem_free()
    if freeMem < 20000:
        lastValue = inList.pop(-1)
        while index < lengthList:
            inList.pop(index)
            lengthList = len(inList)-1
            index += 1
        inList.append(lastValue)
    # return List, hopefully smaller
    return inList


def generateMessageList(inEventTime,
                        inTimeDiff,
                        inMqttClientUniqueId,
                        inMessageType,
                        inMessageContent,
                        ):
    outWlanData = []
    (year, month, day,
     hour, minute, seconds,
     weekday, yearday) = time.localtime(inTimeDiff + inEventTime)
    tmpData = [year,
               month,
               day,
               hour,
               minute,
               seconds,
               weekday,
               yearday,
               inMqttClientUniqueId,
               inMessageType,
               ]
    printDebug("inMessageContent", inMessageContent)
    print("generateMessageList")
    print("MemInfo", micropython.mem_info())
    if inMessageType == MESSAGE_TYPES["wlanScan"]:
        for aWlan in inMessageContent:
            listOfLists = tmpData.copy()
            print("CopyMemInfo", micropython.mem_info())
            printDebug("aWlan", aWlan)
            for field in aWlan:
                printDebug("field", field)
                listOfLists.append(field)
            outWlanData.append(listOfLists)
    elif inMessageType in LIST_MESSAGE_TYPES:
        aList = tmpData.copy()
        for aPart in inMessageContent:
            printDebug("aList", aList)
            aList.append(aPart)
        outWlanData = aList.copy()
    else:
        singleValue = tmpData.copy()
        singleValue.append(inMessageContent)
        outWlanData = singleValue.copy()
    printDebug("outWlanData", outWlanData)
    return outWlanData


def httpGet(url):
    _, _, host, path = url.split('/', 3)
    addr = socket.getaddrinfo(host, 80)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s.send(bytes('GET /%s HTTP/1.0\r\nHost: %s\r\n\r\n' % (path, host), 'utf8'))
    while True:
        data = s.recv(100)
        if not data:
            break
    s.close()


def httpMeasurement():
    i = 0
    print("Starting",
          CONFIG["httpRepeat"],
          "times http measurement with URL",
          CONFIG["httpURL"],
          "while sleeping",
          CONFIG["httpSleepMS"],
          "ms")
    while i < CONFIG["httpRepeat"]:
        i += 1
        print("Run number", i)
        httpGet(CONFIG["httpURL"])
        time.sleep_ms(CONFIG["httpSleepMS"])
    print("Finished HTTP Measurement.")


def printDebug(inName, inVariable):
    if CONFIG["debug"]:
        if isinstance(inVariable, list):
            print("")
        print(inName, type(inVariable), inVariable)
        time.sleep_ms(100)


def mqttApplyConfig(inConfigData):
    for key in inConfigData.keys():
        CONFIG[key] = inConfigData[key]


def mqttCallback(inMqttTopic, inMqttReceived):
    '''
    Message example:
        {
        "hashType": XXX,
        "hashSum": XXX,
        "content":
            {
            "mqttArea": XXX,
            "mqttClientUniqueId": XXX,
            "mqttGroup": XXX,
            "config":
                {
                    "connectTerm": 121,
                    "debug": False,
                    .....
                }
            }
        }
    '''
    global MQTTRECEIVED
    MQTTRECEIVED.append(inMqttReceived)


def mqttCheckMessageHash(inMsgForMe):
    checkedData = {}
    checkedData["checkedState"] = False
    print("Checking message integrity")
    printDebug("inMsgForMe", inMsgForMe)
    hashType = inMsgForMe["mqttHashType"].lower()
    printDebug("hashType", hashType)
    if hashType == "sha256":
        print("Using SHA256 Hash")
        content = str(inMsgForMe["content"])
        hashThis = hashlib.sha256(content)
        for oldHash in MQTTHASH:
            hashThis.update(oldHash)
        binaryDigest = ubinascii.hexlify(hashThis.digest())
        stringDigest = binaryDigest.decode("UTF-8")
        printDebug("stringDigest", stringDigest)
        if stringDigest == inMsgForMe["mqttHashSum"]:
            print("Hash check was sucessful")
            checkedData = inMsgForMe["content"]
            checkedData["checkedState"] = True
            MQTTSTATS["goodMsgs"] += 1
        else:
            print("Failed hash check")
            MQTTSTATS["badMsgs"] += 1
    else:
        print("Found no suitable hash algorithmen")
    # return Dictionary
    return checkedData


def mqttCheckReceiver(inDict):
    conditionsMet = 0
    receiverDict = {}
    receiverDict["receiver"] = False
    content = inDict["content"]
    for ident in CONFIG["mqttIdentifiers"]:
        if (content[ident] == CONFIG[ident] or
           content[ident] == "ALL"):
                conditionsMet += 1
    if conditionsMet == 3:
        print("We got a message.")
        receiverDict = inDict
        receiverDict["receiver"] = True
        MQTTSTATS["acceptedMsgs"] += 1
    else:
        print("Message is not for us.")
        MQTTSTATS["droppedMsgs"] += 1
    # return Dictionary
    return receiverDict


def mqttCollectMessages(inMqttBroker=CONFIG["mqttBroker"],
                        inMqttClientUniqueId=CONFIG["mqttClientUniqueId"],
                        inMqttTopic=CONFIG["mqttConfigTopic"],
                        ):
    global MQTTRECEIVED
    MQTTRECEIVED = []
    outMqttData = []
    countMsg = 0
    mqttClient = MQTTClient(inMqttClientUniqueId,
                            inMqttBroker,
                            ssl=CONFIG["mqttSSL"],
                            user=CONFIG["mqttUser"],
                            password=CONFIG["mqttPassword"],
                            )
    mqttLastWill = ("-1, -1, -1, -1, -1, -1, -1, -1, -1, " +
                    inMqttClientUniqueId + ", " +
                    MESSAGE_TYPES["mqttErrorMessage"] + ", " +
                    "UngracefulDisconnect, " +
                    "Ungraceful disruption of MQTT collect, "
                    )
    mqttClient.set_last_will(inMqttTopic, mqttLastWill)
    mqttClient.set_callback(mqttCallback)
    print("Trying to collect the MQTT Messages.", inMqttTopic)
    print("MQTTSTATS", MQTTSTATS)
    try:
        mqttClient.connect()
        print("Subscribe to", inMqttTopic)
        mqttClient.subscribe(topic=inMqttTopic)
        while CONFIG["mqttReceivedMax"] > countMsg:
            print("Checking for MQTT message")
            mqttClient.check_msg()
            countMsg += 1
            time.sleep_ms(200)
        MQTTSTATS["receivedMsgs"] += len(MQTTRECEIVED)
        print("MQTTRECEIVED", MQTTRECEIVED)
        mqttProcess()
        print("Message(s) of MQTT were processed.")
        print("MQTTSTATS", MQTTSTATS)
        time.sleep(1)
        mqttClient.disconnect()
    except Exception as e:
        print("MQTT collections failed.")
        sys.print_exception(e)
        errorMessage = mqttErrorMessage(inMqttClientUniqueId,
                                        "Exception",
                                        "MQTTClientConnectError",
                                        str(e),
                                        )
        outMqttData.append(errorMessage)
        return outMqttData


def mqttCommit(ioMqttCounter,
               inMqttBroker,
               inMqttTopic,
               inMqttClientUniqueId,
               ioMqttData):
    mqttClient = MQTTClient(inMqttClientUniqueId,
                            inMqttBroker,
                            ssl=CONFIG["mqttSSL"],
                            user=CONFIG["mqttUser"],
                            password=CONFIG["mqttPassword"],
                            )
    mqttLastWill = ("-1, -1, -1, -1, -1, -1, -1, -1, -1, " +
                    inMqttClientUniqueId + ", " +
                    MESSAGE_TYPES["mqttErrorMessage"] + ", " +
                    "UngracefulDisconnect, " +
                    "Ungraceful disruption of MQTT commit, "
                    )
    printDebug("mqttLastWill", mqttLastWill)
    mqttClient.set_last_will(inMqttTopic, mqttLastWill)
    try:
        mqttClient.connect()
        print("## Connected with MQTT Broker", inMqttBroker)
        printDebug("ioMqttData", ioMqttData)
        ioMqttCounter = mqttPublish(ioMqttCounter,
                                    mqttClient,
                                    inMqttTopic,
                                    ioMqttData)
    except Exception as e:
        sys.print_exception(e)
        errorMessage = mqttErrorMessage(inMqttClientUniqueId,
                                        "Exception",
                                        "MQTTClientConnectError",
                                        str(e),
                                        )
        ioMqttData.append(errorMessage)
    try:
        mqttClient.disconnect()
    except Exception as e:
        sys.print_exception(e)
        errorMessage = mqttErrorMessage(inMqttClientUniqueId,
                                        "Exception",
                                        "MQTTClientDisconnectError",
                                        str(e),
                                        )
        ioMqttData.append(errorMessage)
    return ioMqttCounter


def mqttErrorMessage(inMqttClientUniqueId,
                     inErrorType,
                     inErrorDescription,
                     inErrorMessage,
                     ):
    (year, month, day,
     hour, minute, seconds,
     weekday, yearday) = time.localtime()
    osErrorMessage = inErrorType + " has been triggered by mqttCommit"
    outTime = [year, month, day,
               hour, minute, seconds,
               weekday, yearday]
    outMessage = [inMqttClientUniqueId,
                  MESSAGE_TYPES["mqttErrorMessage"],
                  inErrorType,
                  osErrorMessage,
                  ]
    print(osErrorMessage)
    output = outTime + outMessage
    # return List
    return output


def mqttPublish(ioMqttCounter, inMqttClient, inMqttTopic, ioMqttData):
    outData = str(ioMqttCounter) + ", "
    printDebug("ioMqttData[0]", ioMqttData[0])
    firstList = ioMqttData.pop(0)
    if isinstance(firstList, list):
        for i in firstList:
            outData.join(str(i))
            outData.join(", ")
    else:
        outData.join(firstList)
    printDebug("outData", outData)
    inMqttClient.publish(inMqttTopic, outData)
    ioMqttCounter += 1
    if len(ioMqttData) > 0:
        ioMqttCounter = mqttPublish(ioMqttCounter,
                                    inMqttClient,
                                    inMqttTopic,
                                    ioMqttData)
    return ioMqttCounter


def mqttProcess():
    global MQTTRECEIVED
    for message in MQTTRECEIVED:
        printDebug("MQTTRECEIVED", MQTTRECEIVED)
        firstMsg = MQTTRECEIVED.pop(0)
        printDebug("firstMsg", firstMsg)
        msgDict = json.loads(firstMsg)
        msgForMe = mqttCheckReceiver(msgDict)
        if msgForMe["receiver"]:
            checkedData = mqttCheckMessageHash(msgForMe)
            if checkedData["checkedState"]:
                print("Found correct data")
                if "config" in checkedData:
                    print("Config was found in checkedData")
                    mqttApplyConfig(checkedData["config"])
            else:
                print("No correct data")
        print("CONFIG", CONFIG)


def scanWLAN(inNic):
    availableAuthModes = {
        0: "open",
        1: "WEP",
        2: "WPA-PSK",
        3: "WPA2-PSK",
        4: "WPA/WPA2-PSK",
        5: "WPA Enterprise",
        6: "P2P PBC",
        7: "P2P PIN KEYPAD",
        8: "P2P PIN DISPLAY",
        9: "P2P PIN AUTO",
        }
    outMessageList = []
    # interface has to be in disconnected mode for a scan
    print("## Going to scan for available WLAN networks")
    disconnectMessage = disconnectWLAN(inNic)
    outMessageList.append(disconnectMessage)
    # get available WLAN networks
    scanData = inNic.scan()
    print("\n## Found WLAN networks")
    printDebug("scanData", scanData)
    for foundWLAN in scanData:
        ssid = foundWLAN[0].decode("UTF-8")
        bssid = ubinascii.hexlify(foundWLAN[1]).decode("UTF-8")
        channel = foundWLAN[2]
        rssi = foundWLAN[3]
        hidden = foundWLAN[5]
        authModeInt = foundWLAN[4]
        if authModeInt in availableAuthModes:
            authMode = availableAuthModes[authModeInt]
        else:
            authMode = "Unkown mode " + str(authModeInt)
        print("SSID:", ssid,
              "BSSID:", bssid,
              "Channel:", channel,
              "RSSI:", rssi,
              "Authmode:", authMode,
              "Hidden:", hidden,
              )
        outMessageList.append([ssid, bssid, channel, rssi, authMode, hidden])
    print("\n")
    printDebug("outMessageList", outMessageList)
    # return List of List
    return outMessageList


def setLocalTime(ioNtpLastSuccess):
    outNtpResult = False
    outTimeDiff = 0
    randomDelay = randint(0, CONFIG["maximumRandomSecondsDelay"])
    lastNtp = time.time() - ioNtpLastSuccess - randomDelay
    if lastNtp > CONFIG["ntpBetween2Runs"]:
        (year, month, day,
         hour, minute, seconds,
         weekday, yearday) = time.localtime()
        print("Year:", year,
              "Month:", month,
              "Day:", day,
              "Hour:", hour,
              "Minute:", minute,
              "Seconds", seconds)
        try:
            outTimeDiff = ntptime.time() - time.time()
            if outTimeDiff > 1:
                checkState(tryNtp)
            outNtpResult = True
            ioNtpLastSuccess = time.time()
        except Exception as e:
            sys.print_exception(e)
        (year, month, day,
         hour, minute, seconds,
         weekday, yearday) = time.localtime()
        print("New Time:", year, month, day, hour, minute, seconds)
    return outTimeDiff, outNtpResult, ioNtpLastSuccess


def startupSequenz(inNic):
    '''
    After the boot process this function runs to scan the ẂLAN first,
    set the time by NTP.
    '''
    failedConnectTimeList = []
    outConnectTime = time.time()
    outWlanData = []
    outNtpResult = False
    scanTimeList = []
    scanDataList = []
    eventTimer = time.time()
    startTime = time.time()
    print("## Getting started")
    inNic.active(True)
    # get WLAN connection
    while not inNic.isconnected():
        scanTimeList.append(time.time())
        scanDataList.append(scanWLAN(inNic))
        garbageCollectList(scanTimeList)
        garbageCollectList(scanDataList)
        print("Length davor", len(scanDataList))
        print("MemInfo", micropython.mem_info())
        outConnectData, notUsed = connectWLAN(inNic,
                                              CONFIG["wlanSsid"],
                                              CONFIG["wlanSecret"]
                                              )
        failedConnectTimeList.append(time.time())
        garbageCollectList(failedConnectTimeList)
        eventTimer = eventScheduler(eventTimer,)
        print("Length danach", len(scanDataList))
        print("MemInfo", micropython.mem_info())
    if len(failedConnectTimeList) > 0:
        outConnectTime = failedConnectTimeList.pop(-1)
    # get the time by ntp
    print("NTP")
    print("MemInfo", micropython.mem_info())
    while not outNtpResult:
        timeDiff, outNtpResult, ioNtpLastSuccess = setLocalTime(-9999)
        eventTimer = eventScheduler(eventTimer,)
    generatedMessage = generateMessageList(startTime,
                                           timeDiff,
                                           CONFIG["mqttClientUniqueId"],
                                           MESSAGE_TYPES["deviceStart"],
                                           "Device has been started",
                                           )
    outWlanData.append(generatedMessage)
    print("Generate scan messages with timestamp")
    print("MemInfo", micropython.mem_info())
    for scanTime in scanTimeList:
        for scanData in scanDataList:
            generatedMessage = generateMessageList(
                                    scanTime,
                                    timeDiff,
                                    CONFIG["mqttClientUniqueId"],
                                    MESSAGE_TYPES["wlanScan"],
                                    scanData,
                                    )
            # Combine a list of lists
            outWlanData = outWlanData + generatedMessage
    connectDataFailed = [
        "Failure", "Failed to connected to SSID " + CONFIG["wlanSsid"]
        ]
    print("Generate failed messages with timestamp")
    print("MemInfo", micropython.mem_info())
    for failedConnectTime in failedConnectTimeList:
        generatedMessage = generateMessageList(
                                failedConnectTime,
                                timeDiff,
                                CONFIG["mqttClientUniqueId"],
                                MESSAGE_TYPES["connect"],
                                connectDataFailed,
                                )
        outWlanData.append(generatedMessage)
    print("Generate connect messages with timestamp")
    print("MemInfo", micropython.mem_info())
    connectDataSuccess = [
        "Success", "Device connected to SSID " + CONFIG["wlanSsid"]
        ]
    generatedMessage = generateMessageList(outConnectTime,
                                           timeDiff,
                                           CONFIG["mqttClientUniqueId"],
                                           MESSAGE_TYPES["connect"],
                                           connectDataSuccess,
                                           )
    outWlanData.append(generatedMessage)
    printDebug("outWlanData", outWlanData)
    return outWlanData, outConnectTime, outNtpResult, ioNtpLastSuccess


def statusWLAN(inNic):
    output = ["UnknownError", "WLAN Status reported an error", "Unknown"]
    # get status of WLAN
    try:
        wlanIfconfig = inNic.ifconfig()
        wlanRSSI = inNic.status("rssi")
        wlanSSID = inNic.config("essid")
        ipAddress = wlanIfconfig[0]
        netmask = wlanIfconfig[1]
        router = wlanIfconfig[2]
        dns = wlanIfconfig[3]
        output = [ipAddress,
                  netmask,
                  router,
                  dns,
                  wlanSSID,
                  wlanRSSI,
                  ]
        print("\n## Configuration of WLAN interface")
        print("IP-address:", ipAddress,
              "Netmask:", netmask,
              "Router:", router,
              "DNS:", dns,
              "SSID:", wlanSSID,
              "RSSI:", wlanRSSI,
              )
        print("\n")
        return output
    except Exception as e:
        sys.print_exception(e)
        output = ["Exception", "WLAN Status reported an error", str(e)]
        return output


def statusSystem():
    output = [
              sys.version,
              sys.implementation[0],
              sys.implementation[1],
              gc.mem_alloc(),
              gc.mem_free(),
              ]
    for key in MQTTSTATS.keys():
        output.append(MQTTSTATS[key])
    # return Dictionary
    return output


def tryNtp(notUsed):
    try:
        ntptime.settime()
    except Exception as e:
        sys.print_exception(e)
        return False
    return True


def main():
    '''
    After the startup this functions collects some data, depending
    on the state of the WLAN connection.
    '''
    gc.enable()
    micropython.alloc_emergency_exception_buf(5000)
    try:
        nic = network.WLAN(network.STA_IF)
        mqttCounter = 0
        eventTimer = time.time()
        wlanData, connectTime, ntpResult, ntpLastSuccess = startupSequenz(nic)
    except Exception as e:
        sys.print_exception(e)
        machine.reset()
        eventTimer = eventScheduler(ioEventTimer,)
    while True:
        try:
            printDebug("wlanData", wlanData)
            printDebug("connectTime", connectTime)
            printDebug("eventTimer", eventTimer)
            printDebug("mqttCounter", mqttCounter)
            if nic.isconnected():
                (
                 wlanData,
                 connectTime,
                 eventTimer,
                 mqttCounter,
                 ntpResult,
                 ntpLastSuccess,
                 ) = connectedSchedule(
                                    nic,
                                    wlanData,
                                    connectTime,
                                    eventTimer,
                                    mqttCounter,
                                    ntpResult,
                                    ntpLastSuccess,
                                    )
            else:
                (
                 wlanData, connectTime, eventTimer
                 ) = disconnectedSchedule(
                                    nic,
                                    wlanData,
                                    connectTime,
                                    eventTimer,
                                    )
            gc.collect()
        except Exception as e:
            sys.print_exception(e)
            machine.reset()


if __name__ == "__main__":
    main()
