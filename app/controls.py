__author__ = 'GrMartin'

from decorators import *
import threading, time, datetime
import serial, csv
from config import *

##############################
# Arduino Commands
#
# B = Byte
# B1 B2
# 9  9 - Turn off All
# 1  1 - Send current values
# B  0 - Turn off object B
# B  1 - Turn on object  B
# B  X - Set object B to X
#
# Serial calls to Arduino always return all current values
# (message is 30 bytes long)
##############################

class SocketTracker():
    def __init__(self):
        self.sockets=[]


class ArduinoConnectionError(Exception):
    def __str__(self):
        return "Could not connect to arduino"

class ArduinoTools:
    def __init__(self, port, baudrate):
        self.serial_lock = threading.RLock()
        self.lastUpdate = datetime.datetime.utcnow()
        self.dataStorageDir = DATASTORAGEDIR
        self.socketCount = 0

        # keep track of class objects by assigned ID
        self.id_obj_list = {}

        #add arduino elements
        self.firebox1 = FireBox([10,20], self)
        for i in [10, 20]:
            self.id_obj_list[str(i)] = self.firebox1.returnIdObj(i)

        self.firebox2 = FireBox([11,21], self)
        for i in [11, 21]:
            self.id_obj_list[str(i)] = self.firebox2.returnIdObj(i)

        self.coldSmoker = ColdSmoker([12, 13, 30], self)
        for i in [12, 13, 30]:
            self.id_obj_list[str(i)] = self.coldSmoker.returnIdObj(i)

        self.thermometers = []
        for i in range(8): # 8 Thermometers
            self.thermometers.append(Thermometer(50+i, self))
            self.id_obj_list[str(50+i)] = self.thermometers[i]

        self.intervalRecordReadingStopFlag = threading.Event()
        self.intervalRecordReadingStopFlag.set()

        self.intervalSocketReadingStopFlag = threading.Event()
        self.intervalSocketReadingStopFlag.set()

        self.initiateSerialConnection(port, baudrate)

    def initiateSerialConnection(self, port, baudrate):
        self.ser = serial.Serial(port, baudrate)
        i = 0
        while self.ser.in_waiting < 1:
            time.sleep(0.1)
            i +=1
            if i > 120*10:
                raise ArduinoConnectionError()

        self.ser.write("11")
        time.sleep(0.5)
        self.ser.flushInput()


    def talk_with_arduino(self, msg):
        self.serial_lock.acquire()
        # send serial msg
        if self.ser.in_waiting > 0 : self.ser.flushInput()
        self.ser.write(msg)
        i = 0
        while self.ser.in_waiting < 1:
            time.sleep(0.1)
            i+=1
            if i > 120*10:
                raise ArduinoConnectionError()
        returnMsg = self.ser.read(30)
        self.serial_lock.release()
        self.updateArduino(returnMsg)

    def updateArduino(self, updateStr):
        self.lastUpdate = datetime.datetime.utcnow()
        for i in range(0, len(updateStr), 2):
            ard_id = ord(updateStr[i])
            self.id_obj_list[str(ard_id)].updateStatus(ord(updateStr[i+1]))

    def updateReadings(self):
        # call to update arduino values
        msg = chr(1)*2
        self.talk_with_arduino(msg=msg)

    def turnOffAll(self):
        msg = chr(9)+chr(9)
        self.talk_with_arduino(msg)

    def start_interval_record_readings(self, interval):
        if not self.intervalRecordReadingStopFlag.isSet():
            print "Interval record readings already running"
            return 0
        print "Starting Inverval readings"

        @timedLoopCall(interval)
        def sample_status(self):
            print time.ctime(), "\t",
            self.updateReadings()
            self.writeCurrentDataToCSV()

        self.intervalRecordReadingStopFlag =  sample_status(self) #Return stop flag

    def stop_interval_record_readings(self):
        self.intervalRecordReadingStopFlag.set()

    def start_socket_interval_readings(self, interval):
        if not self.intervalSocketReadingStopFlag.isSet():
            print "Interval readings already running"
            return 0
        print "Starting Inverval readings"

        @timedLoopCall(interval)
        def sample_status(self):
            print time.ctime(), "\t",
            self.updateReadings()

        self.intervalSocketReadingStopFlag =  sample_status(self) #Return stop flag

    def stop_socket_interval_readings(self):
        self.intervalSocketReadingStopFlag.set()

    def writeCurrentDataToCSV(self):
        data = [self.lastUpdate.strftime("%Y-%m-%d %H:%M:%S"),
                self.firebox1.heatingElement.status,
                self.firebox1.woodAuger.status,
                self.firebox2.heatingElement.status,
                self.firebox2.woodAuger.status,
                self.coldSmoker.heatingElementTop.status,
                self.coldSmoker.heatingElementBottom.status,
                self.coldSmoker.airPump.status]

        for thermo in self.thermometers:
            data.append(thermo.temp)

        datafileDir = os.path.join(self.dataStorageDir, str(self.lastUpdate.year), str(self.lastUpdate.month))
        if not os.path.exists(datafileDir):
            os.makedirs(datafileDir)
        dataFilename = os.path.join(datafileDir, "%02d.csv") % self.lastUpdate.day

        if not os.path.isfile(dataFilename):
            f = open(dataFilename, "wb")
            f.write("UTC Time, firebox1,,firebox2,,coldsmoker,,,thermometers\n")
            f.write(",Heating Element,Wood Auger,Heating Element,Wood Auger,Top Heating Element, Bottom Heating Element, Air Pump,")
            for i in range(len(self.thermometers)):
                f.write("T"+str(i+1)+",")
            f.write("\n")
        else:
            f = open(dataFilename, "ab")
        csvF = csv.writer(f, delimiter=",")
        csvF.writerow(data)
        f.close()

# Combined Elements

class FireBox:
    def __init__(self, ard_ids, ard_parent):
        self.heatingElement = HeatingElement(ard_ids[0], ard_parent)
        self.woodAuger = WoodAuger(ard_ids[1], ard_parent)

    def returnIdObj(self, ard_id):
        if self.heatingElement.id == ard_id:
            return self.heatingElement
        elif self.woodAuger.id == ard_id:
            return self.woodAuger
        else: return None

class ColdSmoker:
    def __init__(self, ard_ids, ard_parent):
        self.heatingElementBottom = HeatingElement(ard_ids[0], ard_parent)
        self.heatingElementTop = HeatingElement(ard_ids[1], ard_parent)
        self.airPump = AirPump(ard_ids[2], ard_parent)

    def returnIdObj(self, ard_id):
        if self.heatingElementBottom.id == ard_id:
            return self.heatingElementBottom
        elif self.heatingElementTop.id == ard_id:
            return self.heatingElementTop
        elif self.airPump.id == ard_id:
            return self.airPump
        return None

# Base Elements

class Thermometer:
    def __init__(self, ard_id, ard_parent):
        self.id = ard_id
        self.ard_parent = ard_parent
        self.temp = -1

    def updateStatus(self, ardReturnVal):
        # read thermometers... need to add the voltage conversion algorithm here
        self.temp = ardReturnVal

class onOffElement:
    def __init__(self, ard_id, ard_parent):
        self.id = ard_id
        self.ard_parent = ard_parent
        self.status = "off"

    def turnOn(self):
        # Turn on Heating Element
        msg = chr(self.id)+chr(1)
        self.ard_parent.talk_with_arduino(msg)

    def turnOff(self):
        # Turn off Heating Element
        msg = chr(self.id)+chr(0)
        self.ard_parent.talk_with_arduino(msg)

    def updateStatus(self, ardReturnVal):
        if ardReturnVal == 1:
            self.status = "on"
        else:
            self.status = "off"

class HeatingElement(onOffElement):
    def __init__(self, ard_id, ard_parent):
        '''heating element args=(ard_id, ard_parent)'''
        onOffElement.__init__(self, ard_id, ard_parent)

class WoodAuger(onOffElement):
    def __init__(self, ard_id, ard_parent):
        '''wood auger element args=(ard_id, ard_parent)'''
        onOffElement.__init__(self, ard_id, ard_parent)

class AirPump(onOffElement):
    def __init__(self, ard_id, ard_parent):
        '''air pump element args=(ard_id, ard_parent)'''
        onOffElement.__init__(self, ard_id, ard_parent)

