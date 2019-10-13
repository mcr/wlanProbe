class mQ:

    def __init__(self, inUniqueID):
        self._highPrioQ = []
        self._highPrioQnoNTP = []
        self._lowPrioQ = []
        self._lowPrioQnoNTP = []
        self._messageCounter = 0
        self._ntpHasBeenSet = False
        self._timeDiff = 0
        self._uniqueID = inUniqueID

    def uniqueID(self):
        return self._uniqueID

    def addMsg(self, inNewMessage, inPriority="low"):
        '''
        Receives a dictionary and saves in a message queue.
        Dictionary looks like:
        { "seconds": 1337, "messageType": "Foo", "messageContent": "Bar",}
        '''
        if isinstance(inNewMessage, dict):
            if inPriority == "high" and self._ntpHasBeenSet:
                self._highPrioQ.append(inNewMessage)
            elif inPriority == "low" and self._ntpHasBeenSet:
                self._lowPrioQ.append(inNewMessage)
            elif inPriority == "high" and not self._ntpHasBeenSet:
                self._highPrioQnoNTP.append(inNewMessage)
            else:
                self._lowPrioQnoNTP.append(inNewMessage)
        else:
            raise TypeError("Incoming message is not a dictionary.")

    def _fixTimestamp(self):
        for msg in self._highPrioQnoNTP:
            msg["seconds"] += self._timeDiff
            addMsg(msg, "high")
            self._highPrioQnoNTP.pop(0)
            for i in self._lowPrioQnoNTP:
                msg["seconds"] += self._timeDiff
                addMsg(msg, "low")
                self._lowPrioQnoNTP.pop(0)

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
        return inList

    def _generateMessageList(self,
                            inMessage,
                            ):
        '''
        Receives a single message in a dictionary and returns one.
        '''
        (year, month, day,
         hour, minute, seconds,
         weekday, yearday) = time.localtime(inMessage["seconds"])
        outWlanData = {
            "messageCounter": self._messageCounter,
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "minute": minute,
            "seconds": seconds,
            "weekday": weekday,
            "yearday": yearday,
            "uniqueID": self._uniqueID,
            "messageType": inMessage["messageType"],
            "messageContent": inMessage["messageContent"],
        }

        self._messageCounter += 1
        return outWlanData

    def getMsg(self):
        '''
        Returns one dictionary if there is a message.
        '''
        totalL, lenHp, _ = self.lenQ()
        if totalL == 0:
            output = {}
        elif lenHp != 0:
            msg = self._highPrioQ.pop(0)
            output = self._generateMessageList(msg)
        else:
            msg = self._lowPrioQ.pop(0)
            output = self._generateMessageList(msg)
        return output

    def lenQ(self):
        lenHp = len(self._highPrioQ)
        lenLp = len(self._lowPrioQ)
        totalL = lenHp + lenLp
        return totalL, lenHp, lenLp

    def lenQnoNTP(self):
        lenHp = len(self._highPrioQnoNTP)
        lenLp = len(self._lowPrioQnoNTP)
        totalL = lenHp + lenLp
        return totalL, lenHp, lenLp

    def setTimeDiff(self, inTimeDiff):
        self._timeDiff = inTimeDiff
        self._ntpHasBeenSet = True
        totalL, _, _, = self.lenQnoNTP()
        if totalL == 0:
            self._fixTimestamp()
