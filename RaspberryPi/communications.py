"""
Author: David Jorge

This library acts as an API for communicating with the SIM7600X 4G Rpi hat.
"""

import RPi.GPIO as GPIO
import serial
import time
import binascii
import detect
import random

# Initialize UART serial connection
ser = serial.Serial("/dev/ttyS0", 115200)
ser.flushInput()

# Initialize APN and misc variables
power_key = 4
rec_buff = ''
APN = 'payandgo.o2.co.uk'


def power_on(power_key):
    """
    Turn on SIM76000X modem.

    :param power_key: Power pin on modem.
    """
    print('SIM7600X is starting:')
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(power_key, GPIO.OUT)
    time.sleep(0.1)
    GPIO.output(power_key, GPIO.HIGH)
    time.sleep(2)
    GPIO.output(power_key, GPIO.LOW)
    time.sleep(1)
    ser.flushInput()
    print('SIM7600X is ready!')


def power_down(power_key):
    """
    Turn off SIM7600X modem.

    :param power_key: Power pin on modem.
    """
    print('SIM7600X is loging off:')
    GPIO.output(power_key, GPIO.HIGH)
    time.sleep(3)
    GPIO.output(power_key, GPIO.LOW)
    time.sleep(1)
    print('SIM7600X is deactivated!')


def AT(command, back, timeout):
    """
    Sends AT command through UART serial connection.

    :param command: AT command to be sent.
    :param back: Expected response by modem.
    :param timeout: Timeout duration.
    :return: Response.
    """
    rec_buff = ''
    ser.write((command + '\r\n').encode())
    time.sleep(timeout)
    if ser.inWaiting():
        time.sleep(0.1)
        rec_buff = ser.read(ser.inWaiting())
    if rec_buff != '':
        if back not in rec_buff.decode():
            print(command + ' ERROR')
            print(command + ' back:\t' + rec_buff.decode())
            return 0
        else:
            print(rec_buff.decode())
            return 1
    else:
        print(command + ' no response')


def send_sms(phone_num, message="hello"):
    """
    Sends an SMS through the SIM7600X modem.

    :param phone_num: Target phone number.
    :param message: Message to be sent.
    """
    AT("AT+CMGF=1", "OK", 1)
    AT("AT+CMGS=\"{}\"".format(phone_num), ">", 2)
    ser.write(message.encode())
    if 1 == AT(b'\x1a'.decode(), 'OK', 5):
        print('Message Sent!')


def init_checks():
    """
    Get hardware and connection information from modem.
    """
    AT("AT+CPIN?", "OK", 1)
    AT("AT+CGMM", "OK", 1)
    AT("AT+CGMR", "OK", 1)
    AT("AT+GSN", "OK", 1)
    AT("AT+COPS?", "OK", 1)
    AT("AT+CSQ", "OK", 1)
    AT("AT+CPSI?", "OK", 1)
    AT("AT+CGREG", "OK", 1)
    AT("AT+CGACT?", "OK", 1)
    AT("AT+CGPADDR", "OK", 1)


def ssl_config():
    """
    Configure SSL certificates and private key for establishing connection over TLS.
    NOTE: Certificate and private key files need to be previously loaded into the modem,
    this can be done by running the following sequence of AT commands over USB:

    AT+CCERTDOWN="cacert.pem", __file_size__
    *PASTE FILE CONTENTS
    AT+CCERTDOWN="clientcert.pem", __file_size__
    *PASTE FILE CONTENTS
    AT+CCERTDOWN="clientkey.pem", __file_size__
    *PASTE FILE CONTENTS
    """
    AT("AT+CCERTLIST", "OK", 2)
    AT("AT+CSSLCFG=\"sslversion\",0,4", "OK", 1)
    AT("AT+CSSLCFG=\"authmode\",0,2", "OK", 1)
    AT("AT+CSSLCFG=\"cacert\",0,\"cacert.pem\"", "OK", 1)
    AT("AT+CSSLCFG=\"clientcert\",0,\"clientcert.pem\"", "OK", 1)
    AT("AT+CSSLCFG=\"clientkey\",0,\"clientkey.pem\"", "OK", 1)


def mqtt_conn(topic="aws/things/simcom7600_device01/", message="SIMCom Connected!",
              endpoint="a34ql9bpsx9ogl-ats.iot.eu-west-2.amazonaws.com", port="8883"):
    """
    Configures and starts MQTT session.

    :param topic: MQTT WILL topic.
    :param message: MQTT WILL message
    :param endpoint: MQTT endpoint
    :param port: Target Port
    """
    AT("AT+CMQTTSTART", "+CMQTTSTART: 0", 1)
    AT("AT+CMQTTACCQ=0,\"SIMCom_client01\",1", "OK", 1)
    AT("AT+CMQTTSSLCFG=0,0", "OK", 1)
    AT("AT+CMQTTWILLTOPIC=0,{}".format(len(topic)), ">", 2)
    ser.write(topic.encode())
    time.sleep(2)
    AT("AT+CMQTTWILLMSG=0,{},1".format(len(message)), ">", 2)
    ser.write(message.encode())
    time.sleep(2)
    AT("AT+CMQTTCONNECT=0,\"tcp://{}:{}\",60,1".format(endpoint, port), "+CMQTTCONNECT: 0,0", 4)


def mqtt_disc():
    """
    Disconnects from current MQTT session.
    """
    AT("AT+CMQTTDISC=0,120", "OK", 1)
    AT("AT+CMQTTREL=0", "OK", 1)
    AT("AT+CMQTTSTOP", "OK", 1)


def mqtt_sub(topic="aws/things/simcom7600_device01/"):
    """
    Subscribe to topic in current MQTT session.

    :param topic: Subscription topic.
    """
    AT("AT+CMQTTSUBTOPIC=0,{},1".format(len(topic)), ">", 2)
    ser.write(topic.encode())
    time.sleep(2)
    AT("AT+CMQTTSUB=0", "OK", 1)


def mqtt_pub(payload, topic="aws/things/simcom7600_device01/", raw=False):
    """
    Publish to current MQTT session.

    :param payload: Publish message.
    :param topic: Publish topic.
    :param raw: Flags whether or not to encode the data over the UART serial connection.
    """
    AT("AT+CMQTTTOPIC=0,{}".format(len(topic)), ">", 2)
    ser.write(topic.encode())
    time.sleep(2)
    AT("AT+CMQTTPAYLOAD=0,{}".format(len(payload)), ">", 2)
    ser.write(payload.encode()) if not raw else ser.write(payload)
    time.sleep(2)
    AT("AT+CMQTTPUB=0,1,60", "+CMQTTPUB: 0,0", 1)


def imgToChunks(byte_arr, chunk_size=5120):
    """
    Converts image bytearray into chunks of hex strings that the modem can transmit over MQTT.

    :param byte_arr: JPEG compressed image in bytearray format.
    :param chunk_size: Size of split
    :return: List of hex strings representing the compressed image.
    """
    l = lambda byte_arr, x: [byte_arr[i:i + x] for i in range(0, len(byte_arr), x)]
    msgs = l(bytes(byte_arr), chunk_size)
    print(binascii.hexlify(bytes(byte_arr)))
    return msgs


def mqtt_sendimg(msgs, headers=None):
    """
    Starts the transmission loop for sending chunks of an image over MQTT.

    :param msgs: List of hex strings representing compressed image.
    :param headers: Relevant metadata to be sent to AWS.
    """
    header = "{Image Start"
    if headers:
        for metadata in headers:
            header += "," + str(metadata)
    header += "}"
    mqtt_pub(header)
    for msg in msgs:
        mqtt_pub(payload=binascii.hexlify(msg), raw=True)
    mqtt_pub("{Image End}")


def gps_init():
    """
    Initialize GPS system.
    """
    AT("AT+CGPS=1,1", "OK", 1)


def gps_getpos():
    """
    Get current GPS coordinates.
    """
    AT("AT+CGPSINFO", '+CGNSINF: ', 1)


def gps_getposdummy():
    """
    Get dummy GPS coordinates.
    :return:
    """
    latitude = 53.06
    longitude = -24.27
    lat = latitude + random.random() * 4
    lon = longitude + random.random() * 11
    return lat, lon


def gps_disc():
    """
    Deactivate the GPS system.
    :return:
    """
    AT("AT+CGPS=0", "OK", 1)


if __name__ == "__main__":
    # gps_init()
    lat, lon = gps_getposdummy()
    # gps_disc()
    img, num = detect.run_model()
    # init_checks()
    # ssl_config()
    # mqtt_conn()
    msgs = imgToChunks(img)
    mqtt_sendimg(msgs, [lat, lon, num])
    # mqtt_disc()
    # power_on(power_key)
    # power_down(power_key)
    # AT("AT", "OK", 1)
    # AT("AT", "OK", 1)
    # init_checks()
    # mqtt_pub("{TEST}")
    # mqtt_disc()
    # send_sms("07505445813", "hello again")
