__author__ = 'GrMartin'

import unittest, random
from coverage import coverage
cov = coverage(branch=True, omit=["GB_venv/*", "tests.py"])
cov.start()

from app import controls
import time
from config import *

class TestCase(unittest.TestCase):
    def setUp(self):
        pass

class testArd(controls.ArduinoTools):
    def __init__(self):
        controls.ArduinoTools.__init__(self, None, None)
        self.dataStorageDir = os.path.join(basedir, "test files\\data")
        self.ids_options_dict={}
        for key in self.id_obj_list.keys():
            if int(key) < 50: self.ids_options_dict[key] = [0, 1]
            else: self.ids_options_dict[key] = range(100,200)

    def initiateSerialConnection(self, port, baudrate):
        pass
    def talk_with_arduino(self, msg):
        self.serial_lock.acquire()
        time.sleep(1)
        print "Fake ard response to", repr(msg)
        response = ""
        for key in self.ids_options_dict.keys():
            if ord(msg[0]) == int(key) and ord(msg[0])<50:
                response += msg
            else:
                if int(key) < 50:
                    if self.id_obj_list[key].status == "on":
                        response += chr(int(key)) + chr(1)
                    else:
                        response += chr(int(key)) + chr(0)
                else:
                    if ord(msg[0]) == 9: # turn all off
                        response += chr(int(key)) + chr(0)
                    else:
                        response += chr(int(key)) + chr(random.choice(self.ids_options_dict[key]))
        self.serial_lock.release()
        self.updateArduino(response)
