# Thanks to https://github.com/cribskip for its help

import uos,machine,binascii,socket,time
from umqtt.robust2 import MQTTClient
from machine import WDT

uart = machine.UART(2)
uart.init(10000, bits=8, parity=None, stop=1, timeout=90)
myFrame = bytearray(200)
watchdog = WDT(timeout=60000) # 1 min timeout

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
serverAddressPort  = ("192.168.3.11",1111)

mqttclient = MQTTClient(binascii.hexlify(machine.unique_id()), '192.168.3.11')
mqtt_prefix = "poolstar"
report_interval = 30

def reset():
    s.close()
    webrepl.stop()
    machine.soft_reset()

def send(data):
    try:
        s.sendto(data, serverAddressPort)
    except Exception as err:
        print("Send error:",err)

def sendmqtt(topic,data):
    if mqttclient.is_conn_issue() :
        print("MQTT connection issue, reconnect")
        mqttclient.connect()
    mqttclient.publish(mqtt_prefix+"/"+topic,data)

def loop():
    counter = 1
    while True:
        watchdog.feed()
        time.sleep_ms(20) # keep WebREPL responsive
        if uart.any():
            copied = uart.readinto(myFrame)
            if (copied >= 49) and (copied <= 52) : # Frame from pump
                water_in_temp       = ((0xFF - myFrame[1]) >> 3) & 0b111111
                air_ambient_temp    = ((0xFF - myFrame[2]) >> 1) & 0b111111
                coil_temp           = ((0xFF - myFrame[3]) >> 1) & 0b111111
                gas_exhaust_temp    = ((0xFF - myFrame[4]) >> 1) & 0b111111
                water_out_temp      = ((0xFF - myFrame[5]) >> 1) & 0b111111
                active              = ((0xFF - myFrame[7]) >> 4) & 0b000001
                print("PUMP Active: {} Water In: {}  Water Out: {}  Coil: {}  Gas Exhaust: {}  Ambient: {}".format(active,water_in_temp, water_out_temp, coil_temp, gas_exhaust_temp, air_ambient_temp))
                #print("{0:5d}".format(copied))
                #print("Counter={}".format(counter))
            elif (copied == 100) : # Frame from panel
                target_temp = ((0xFF - myFrame[4]) >> 1) & 0b111111
                if (myFrame[50] == 0x38) and (myFrame[52] != 0xFF) :
                    time_hour = ((0xFF - myFrame[51]) >> 2) & 0b1111111
                    time_min = ((0xFF - myFrame[52]) >> 1) & 0b1111111
                    print("PANEL Target: {}  Time: {:02d}:{:02d}".format(target_temp,time_hour,time_min))
                elif (myFrame[52] == 0xFF) :
                    on_off = ((0xFF - myFrame[51]) >> 3) & 0b000001
                    print("PANEL Target: {}  On: {}".format(target_temp,on_off))
            #else:
                #print("{0:5d}".format(copied))
            send(str(copied)+";")
            send(binascii.hexlify(myFrame[0:(copied)],';') + "\n")
            if counter > report_interval : 
                counter = 0
            if counter == 0:
                print("Report via MQTT")
                if water_in_temp > 0 : sendmqtt('water_in_temp', str(water_in_temp))
                sendmqtt('air_ambient_temp', str(air_ambient_temp))
                sendmqtt('coil_temp', str(coil_temp))
                sendmqtt('gas_exhaust_temp', str(gas_exhaust_temp))
                sendmqtt('water_out_temp', str(water_out_temp))
                sendmqtt('active',str(active))
                sendmqtt('on',str(on_off))
                sendmqtt('target_temp',str(target_temp))
            counter += 1

#webrepl.stop()
#webrepl.start()
print("Waiting wifi...")
time.sleep(8) # wait for wifi
print("Starting")
mqttclient.connect()
loop()