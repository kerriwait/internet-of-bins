import paho.mqtt.client as mqttClient
import time
import json
import requests
import logging

# TODO: Clean up globals
data = [0] * 10
count = 0
outsideCount = 0
binOutside = False
lastMessage = time.time()


def slackMessage(binState):
    """
    Send a message to slack via the incoming webhooks integration
    :param binState: Boolean representing location of bin
    :return: None
    """
    log = logging.getLogger('iob')

    if binState:
        location = "Out"
    else:
        location = "In"
           
    url = "https://hooks.slack.com/services/{}"
    
    payload = {"text": "Bin is: {}".format(location)}

    headers = {"Content-Type": "application/json"}

    response = requests.request(
        "POST",
        url,
        data=json.dumps(payload),
        headers=headers
    )

    log.debug(response.text)
    return


def on_message(client, userdata, message):
    """
    Callback function to parse incoming messages from the IOB nodes
    :param client: The Paho MQTT client object
    :param userdata: Unused
    :param message: The message object to parse
    :return: None
    """
    # TODO: Refactor me!! Reduce the number of globals we're using here by
    # adding them to the client var

    log = logging.getLogger('iob')
    
    try:
        global count
        global data
        global outsideCount
        global binOutside
        global lastMessage
        
        lastMessage = time.time()
        
        if count > 9:
            count = 1
            average = reduce(lambda x, y: x + y, data) / len(data)
            log.debug("average: " + str(average))
            
            if average > 85:
                outsideCount = outsideCount + 1
            else:
                outsideCount = 0
               
        x = 0
        
        log.debug(outsideCount)
    
        packet = json.loads(message.payload)
        x = abs(packet["rssi"])

        data[count] = x

        # TODO: Clean up logic, it appears to be backwards here
        if outsideCount > 10:
            if not binOutside:
                log.debug("Bin is outside!")
                slackMessage(True)
                binOutside = True
        else:          
            if binOutside:
                log.debug("Bin is inside")
                slackMessage(False)
                binOutside = False
                       
        count += 1
        
    except Exception as e:
        log.exception(e)
        import sys
        sys.exit(1)
    return
        

def on_connect(client, userdata, flags, rc):
    """
    Callback function for connecting to MQTT broker
    :param client: The Paho MQTT client object
    :param userdata: Unused
    :param flags: Unused
    :param rc: Return code
    :return: client.connected_flag
    """
    if rc == 0:
        print("Connected to broker")
        client.connected_flag = True
    else:
        print("Connection failed")
        client.connected_flag = False


class Broker(object):
    """Basic CCHS broker class to hold vars"""
    def __init__(self, address, port, topic):
        self.address = address
        self.port = port
        self.topic = topic


def main():
    log = logging.getLogger('iob')

    # Interval for checking if the bin has moved
    interval = 600

    broker = Broker(
        address="iot.local",
        port=1883,
        topic="happy-bubbles/ble/iob1/raw/c9e49caaeea1"
    )

    # Initialise a client, register functions, connect client to broker, start
    # loop
    client = mqttClient.Client("iobServer")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(broker.address, port=broker.port)
    client.loop_start()

    # Stall until we're connected to the broker
    while not client.connected_flag:
        time.sleep(0.1)

    # After connecting subscribe to our IOB topic
    client.subscribe(broker.topic)

    try:
        while True:
            current_interval = time.time() - lastMessage
            log.debug(current_interval)
            if current_interval > interval:
                if not binOutside:
                    binOutside = True
                    slackMessage(True)
                    log.debug("Bin is outside!")

            time.sleep(60)

    except KeyboardInterrupt:
        log.exception("Exiting due to KeyboardInterrupt")
        client.disconnect()
        client.loop_stop()
        import sys
        sys.exit(1)
    except Exception as e:
        log.exception("Exiting due to Exception")
        client.disconnect()
        client.loop_stop()
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
