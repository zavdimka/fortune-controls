from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.constants import Endian
import numpy as np
import logging

class X4Motor(object):
    MODE_ANGLE = 1
    MODE_SPEED = 2
    MODE_PWM = 3
    MODE_NONE = 0

    def __init__(self, client, settings = None, id = 1, mode = MODE_NONE):
        self._mode = self.MODE_NONE
        self.client = client
        self.stepspermm = 1
        self.reverse = 0
        self.anglezero = 0
        
        if settings:
            self.id = settings.get('id',1)
            if 'I_limit' in settings:
                self.setIlimit(settings.get('I_limit', 5000))
            if 'V_min' in settings:
                self.setVlimit(settings.get('V_min', 11))
            if 'TempShutDown' in settings:
                self.setTempShutDown(settings.get('TempShutDown', 90))
            
            if 'StepsPerMM' in settings:
                self.stepspermm = settings.get('StepsPerMM', 1)
            if 'Reverse' in settings:
                self.reverse = settings.get('Reverse', 0)
                
            if 'PWM_Limit' in settings:
                self.setPWM_Limit(settings.get('PWM_Limit', 300))
            if 'PWM_inc_limit' in settings:
                self.setAngle_PWM_limit(settings.get('PWM_inc_limit', 1))
                
            if 'Mode' in settings:
                self.mode = self.str2mode(settings.get('Mode', 'none'))
                
            if 'TimeOut' in settings:
                self.setTimeout(settings.get('TimeOut', 1))
                
            if 'Angle_PID_P' in settings:
                self.setAngle_PID_P(settings.get('Angle_PID_P', 1))
            if 'Angle_PID_I' in settings:
                self.setAngle_PID_I(settings.get('Angle_PID_I', 1))
            if 'Speed_PID_P' in settings:
                self.setSpeed_PID_P(settings.get('Speed_PID_P', 1))
            if 'Speed_PID_I' in settings:
                self.setSpeed_PID_I(settings.get('Speed_PID_I', 1))
            
        else:
            self.id = id
            self.mode = mode
        
        self.angle = 0
        self.anglezero = self.dstep
        print('id' + str(self.id))
        self.angle = self.readAngle()  #for sensor
        self.sangle = self.angle # for set up
        self.speed = 0
        self.pwm = 0
        self.targetAngle = 0
        #self.setPWM_Limit(500)  # 200 ~2.7A,  400 ~12A,  450 ~16A
        self.clear_error()


    def str2mode(self, str):
        str = str.lower()
        if str == 'Angle'.lower():
            return self.MODE_ANGLE
        if str == 'Speed'.lower():
            return self.MODE_SPEED
        if str == 'PWM'.lower():
            return self.MODE_PWM
        return self.MODE_NONE
        
     

    @property
    def dstep(self):
        a = self.readAngle()
        d = a - self.angle
        self.angle = a
        i = d / self.stepspermm
        if self.reverse:
            i = -i
        return i


    @dstep.setter
    def dstep(self, value):
        if self.reverse:
            value = -value
        d = value * self.stepspermm
        a = d + self.sangle
        #print(f'was {self.sangle:.1f}, setting {d:.1f}, diff {a:.1f}')
        self.sangle = a
        self.setAngle(int(a))
        
    def stepzero(self):
        self.anglezero += self.step

    @property
    def step(self):
        a = self.readAngle()
        self.angle = a
        i = a / self.stepspermm
        if self.reverse:
            i = -i
        i -= self.anglezero
        return i


    @step.setter
    def step(self, value):
        value += self.anglezero
        if self.reverse:
            value = -value
        d = value * self.stepspermm
        self.sangle = d
        self.setAngle(int(d))


    @property
    def mode(self):
        return self._mode

        
    @mode.setter
    def mode(self, value):
        self._mode = value
        if value == self.MODE_ANGLE:
            self.step = self.step
        self.updateMode()
        
    @property
    def speed(self):
        s = self.readSpeed()
        i = s / self.stepspermm
        if self.reverse:
            i = -i
        return i
        
    @speed.setter
    def speed(self, value):
        if self.reverse:
            value = -value
        d = value * self.stepspermm
        self.setSpeed(value)
        
    @property
    def pwm(self):
        return self.readPWM()
        
        
    @pwm.setter
    def pwm(self, value):
        if self.reverse:
            value = -value
        self.setPWM(value)
        
        
    @property    
    def error(self):
        return self.readError()

        
    def setMode(self, mode):
        self.mode = mode

        
    def setAngle(self, angle): # Set up aim to angle and set up angle
        if self.mode != self.MODE_ANGLE:
            self.mode = self.MODE_ANGLE

        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        builder.add_32bit_int(int(angle))
        payload = builder.build()
        self.client.write_registers(4, payload, skip_encode=True, unit=self.id)

        
    def setSpeed(self, speed): # Set up aim to speed and set up speed
        if self.mode != self.MODE_SPEED:
            self.mode = self.MODE_SPEED
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                           wordorder=Endian.Little)
        builder.add_16bit_int(int(speed))
        payload = builder.to_registers()[0]
        self.client.write_register(3, payload, unit=self.id)
        
        
    def setPWM(self, pwm): # Set up aim to pwm and set up pwm
        if self.mode != self.MODE_PWM:
            self.mode = self.MODE_NONE
            self.mode = self.MODE_PWM
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                           wordorder=Endian.Little)
        builder.add_16bit_int(int(pwm))
        payload = builder.to_registers()[0]
        self.client.write_register(2, payload, unit=self.id)

    def release(self):
        self.mode = self.MODE_NONE

    def saferead(self, addr, count, unit, retry = 3 ):
        while retry > 0:
            result = self.client.read_holding_registers(addr, count, unit=unit)
            if hasattr(result, 'registers'):
                return (result, True)
            retry -= 1
        #logging.info(f'addr {addr}, unit {unit}')
        return (None, False)

    def readAngle(self):
        result,success = self.saferead(67, 2, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        return decoder.decode_32bit_int()

    def setTimeout(self,value):
        self.client.write_register(18, int(value/40), unit=self.id)
	
    def readV(self):
        result,success  = self.saferead(64, 1, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        return decoder.decode_16bit_int() / 10000
		
    def readI(self):
        result,success  = self.saferead(65, 1, unit=self.id)
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
        
    def readPWM(self):
        result = self.client.read_holding_registers(71, 1, unit=self.id)
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
        
    def readAllRO(self):
        result = self.client.read_holding_registers(64, 11, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        ans = {}
        ans['V'] = decoder.decode_16bit_int()
        ans['I'] = decoder.decode_16bit_int()
        ans['Temp'] = decoder.decode_16bit_int()
        ans['Angle'] = decoder.decode_32bit_int()
        ans['Speed'] = decoder.decode_16bit_int()
        ans['Vect Angle'] = decoder.decode_16bit_int()
        ans['Vect pwm'] = decoder.decode_16bit_int()
        ans['A'] = decoder.decode_16bit_int()
        ans['B'] = decoder.decode_16bit_int()
        ans['C'] = decoder.decode_16bit_int()
        return ans

    def updateMode(self):
        self.client.write_register(0, self.mode, unit=self.id)
        

    def setID(self, index):
        self.client.write_register(129, index, unit=self.id)
        self.id = index

        
    def setIlimit(self, val):
        i = val * 1000
        self.client.write_register(10, int(i), unit=self.id)

        
    def setVlimit(self, val):
        i = val * 1000
        self.client.write_register(9, int(i), unit=self.id)

        
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
        
    
    def reset(self):
        self.client.write_register(1023, 1023, unit=self.id)
        

        
    def loadsensorconfig(self, filename):
        d = np.load(filename)
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)
        for i in d:
            builder.add_16bit_int(i)
        p= builder.build()
        for i,j in zip(p,range(len(d))):
            self.client.write_register(30+j, i, skip_encode=True, unit=self.id)
    
    def savesensorconfig(self, filename):
        result = self.client.read_holding_registers(30, 12, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        l = [decoder.decode_16bit_int() for i in range(12)]
        s = np.array(l)
        np.save(filename, s)
        
