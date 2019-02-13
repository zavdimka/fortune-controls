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
        self.pwm = 0
        self.targetAngle = 0
        self.setPWM_Limit(500)  # 200 ~2.7A,  400 ~12A,  450 ~16A
        self.clear_error()

        
    @property
    def mode(self):
        return self._mode

        
    @mode.setter
    def mode(self, value):
        self._mode = value
        self.updateMode()

        
    def setMode(self, mode):
        self.mode = mode

        
    def setAngle(self, angle): # Set up aim to angle and set up angle
        if self.mode != self.MODE_ANGLE:
            self.mode = self.MODE_ANGLE

        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        builder.add_32bit_int(angle)
        payload = builder.build()
        self.client.write_registers(4, payload, skip_encode=True, unit=self.id)

        
    def setSpeed(self, speed): # Set up aim to speed and set up speed
        if self.mode != self.MODE_SPEED:
            self.mode = self.MODE_SPEED
        self.speed = int(speed)
        self.updateData()
        
        
    def setPWM(self, pwm): # Set up aim to pwm and set up pwm
        if self.mode != self.MODE_PWM:
            self.mode = self.MODE_NONE
            self.mode = self.MODE_PWM
        self.pwm = int(pwm)
        self.updateData()

    def release(self):
        self.mode = self.MODE_NONE
        
    def setTimeout(self,value):
        self.client.write_register(18, int(value/40), unit=self.id)

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
        return decoder.decode_16bit_int() / 10000
		
    def readI(self):
        result = self.client.read_holding_registers(65, 1, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        return decoder.decode_16bit_int() / 1000
	
    def readSpeed(self):
        result = self.client.read_holding_registers(69, 1, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        return decoder.decode_16bit_int()
	
    def readError(self):
        result = self.client.read_holding_registers(29, 1, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        return decoder.decode_16bit_int()

    def updateMode(self):
        self.client.write_register(0, self.mode, unit=self.id)

    def updateData(self):
        if self.mode == self.MODE_ANGLE:
            pass            
        elif self.mode == self.MODE_SPEED:
            builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                           wordorder=Endian.Little)
            builder.add_16bit_int(self.speed)
            payload = builder.to_registers()[0]
            self.client.write_register(3, payload, unit=self.id)
            
        elif self.mode == self.MODE_PWM:
            builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                           wordorder=Endian.Little)
            builder.add_16bit_int(self.pwm)
            payload = builder.to_registers()[0]
            self.client.write_register(2, payload, unit=self.id)

    def setID(self, index):
        self.client.write_register(129, index, unit=self.id)
        self.id = index

        
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

        
    def setAngle_PID_I(self,i):
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        builder.add_16bit_int(i)
        payload = builder.to_registers()[0]
        self.client.write_register(15, payload, unit=self.id)
        
        
    def setAngle_PID_I_limit(self,i):
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        builder.add_16bit_int(i)
        payload = builder.to_registers()[0]
        self.client.write_register(19, payload, unit=self.id)
       
       
    def setSpeed_PID_I_limit(self,i):
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        builder.add_16bit_int(i)
        payload = builder.to_registers()[0]
        self.client.write_register(20, payload, unit=self.id)

        
    def setSpeed_PID_P(self,i):
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        builder.add_16bit_int(i)
        payload = builder.to_registers()[0]
        self.client.write_register(13, payload, unit=self.id)

        
    def setSpeed_PID_I(self,i):
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        builder.add_16bit_int(i)
        payload = builder.to_registers()[0]
        self.client.write_register(12, payload, unit=self.id)
        
        
    def setPWM_Limit(self, i):
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        builder.add_16bit_int(i)
        payload = builder.to_registers()[0]
        self.client.write_register(21, payload, unit=self.id)
        
        
    def setAngle_PWM_limit(self, i): #PWM increase limit in angle control loop
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        builder.add_16bit_int(i)
        payload = builder.to_registers()[0]
        self.client.write_register(22, payload, unit=self.id)
        
        
    def clear_error(self):
        self.client.write_register(29, 0, unit=self.id)

        
    def loadsensorconfig(self, filename):
        d = np.load(filename)
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        for i in d:
            builder.add_16bit_int(i)
        p= builder.build()
        for i,j in zip(p,range(len(d))):
            self.client.write_register(30+j, i, skip_encode=True, unit=self.id)
