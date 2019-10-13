from messageQueue import mQ


def test_add_bogus_message():
    test_data = "This is not a dictionary"

    mq = mQ(inUniqueID=100)

    try:
        mq.addMsg(test_data)
    except Exception as e:
        assert str(e) == "Incoming message is not a dictionary."


def test_add_lowNoNTP_message():
    test_data = {"seconds": 1337, "messageType": "Foo", "messageContent": "Bar"}

    mq = mQ(inUniqueID=100)

    mq.addMsg(test_data)

    assert mq.lenQ() == (0, 0, 0)
    assert mq.lenQnoNTP() == (1, 0, 1)

def test_add_highNoNTP_message():
    test_data = {"seconds": 1337, "messageType": "Foo", "messageContent": "Bar"}

    mq = mQ(inUniqueID=100)

    mq.addMsg(test_data, inPriority="high")

    assert mq.lenQ() == (0, 0, 0)
    assert mq.lenQnoNTP() == (1, 1, 0)

def test_add_lowNTP_message():
    test_data = {"seconds": 1337, "messageType": "Foo", "messageContent": "Bar"}

    mq = mQ(inUniqueID=100)
    mq.setTimeDiff(1)

    mq.addMsg(test_data)

    assert mq.lenQ() == (1, 0, 1)
    assert mq.lenQnoNTP() == (0, 0, 0)

def test_add_highNTP_message():
    test_data = {"seconds": 1337, "messageType": "Foo", "messageContent": "Bar"}

    mq = mQ(inUniqueID=100)
    mq.setTimeDiff(1)

    mq.addMsg(test_data, inPriority="high")

    assert mq.lenQ() == (1, 1, 0)
    assert mq.lenQnoNTP() == (0, 0, 0)

