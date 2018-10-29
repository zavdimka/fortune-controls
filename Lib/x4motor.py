from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.constants import Endian
from collections import OrderedDict
import numpy as np

class X4Motor():
    MODE_ANGLE = 1
    MODE_SPEED = 2
    MODE_PWM = 3
    MODE_NONE = 0

    def __init__(self, client, id, mode = MODE_NONE):
        self._mode = self.MODE_NONE
        self.client = client
        self.id = id
        self.mode = mode

        self.angle = 0
        self.speed = 0
        super.__init__()

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self._mode = value
        self.updateMode()

    def setMode(self, mode):
        self.mode = mode

    def setAngle(self, angle):
        if self.mode != self.MODE_ANGLE:
            self.mode = self.MODE_ANGLE
        self.angle = int(angle)
        self.updateData()

    def setSpeed(self, speed):
        if self.mode != self.MODE_SPEED:
            self.mode = self.MODE_SPEED
        self.speed = int(speed)
        self.updateData()

    def release(self):
        self.mode = self.MODE_NONE

    def readAngle(self):
        result = self.client.read_holding_registers(67, 2, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        return decoder.decode_32bit_int()
	
	def readV(self):
		result = self.client.read_holding_registers(64, 1, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        return decoder.decode_16bit_int()
		
	def readI(self):
		result = self.client.read_holding_registers(65, 1, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        return decoder.decode_16bit_int()
	
	def readSpeed(self):
		result = self.client.read_holding_registers(69, 1, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        return decoder.decode_16bit_int()
	
	def readError(self):
		result = self.client.read_holding_registers(72, 1, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        return decoder.decode_16bit_int()

    def updateMode(self):
        self.client.write_register(0, self.mode, unit=self.id)

    def updateData(self):
        if self.mode == self.MODE_ANGLE:
            builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                           wordorder=Endian.Little)
            builder.add_16bit_int(self.angle)
            payload = builder.to_registers()
            self.client.write_register(4, payload[0], unit=self.id)
        elif self.mode == self.MODE_SPEED:
            builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                           wordorder=Endian.Little)
            builder.add_16bit_int(self.speed)
            payload = builder.to_registers()[0]
            self.client.write_register(3, payload, unit=self.id)

    def setID(self, index):
        self.client.write_register(129, index, unit=self.id)
		
	def setIlimit(self, val):
		self.client.write_register(10, val, unit=self.id)
		
	def setVlimit(self, val):
		self.client.write_register(9, val, unit=self.id)
		
	def setTempShutDown(self, val):
		self.client.write_register(11, val, unit=self.id)

    def save2flash(self):
        self.client.write_register(130, 0, unit=self.id)

    def setAngle_PID_P(self,i):
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        builder.add_16bit_int(i)
        payload = builder.to_registers()[0]
        self.client.write_register(16, payload, unit=self.id)

    def setAngle_PID_D(self,i):
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        builder.add_16bit_int(i)
        payload = builder.to_registers()[0]
        self.client.write_register(17, payload, unit=self.id)

    def setSpeed_PID_P(self,i):
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        builder.add_16bit_int(i)
        payload = builder.to_registers()[0]
        self.client.write_register(13, payload, unit=self.id)

    def setSpeed_PID_D(self,i):
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        builder.add_16bit_int(i)
        payload = builder.to_registers()[0]
        self.client.write_register(14, payload, unit=self.id)

    def loadsensorconfig(self, filename):
        d = np.load(filename)
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        for i in d:
            builder.add_16bit_int(i)
        p= builder.build()
        payload = b''
        for i in p:
            payload += i
        self.client.write_register(30, payload, skip_encode=True, unit=self.id)
