import sys
sys.path.append('..\Lib')

from pymodbus.client.sync import ModbusSerialClient as ModbusClient #initialize a serial RTU client instance
from x4motor import X4Motor
from modbusbootloader import ModBusBootLoader
import time

client= ModbusClient(method = "rtu", port="COM4", stopbits = 1,
                     bytesize = 8, parity = 'N', baudrate= 115200,
                     timeout = 0.8 )

client.connect()

M = X4Motor(client, 1)

M.setAngle_PID_P(100) #PID P part
M.setAngle_PID_I(1) # PID I part
M.setAngle_PID_I_limit(1000) # PID I integratons limits
M.setAngle_PWM_limit(10)

M.setIlimit(30000)
M.setVlimit(10000)
M.setTempShutDown(100)
M.setPWM_Limit(100)

print("Angle read Demo")
for i in range(100):
    angle = M.readAngle()
    print("Angle is", angle)
    time.sleep(0.1)
    
print("Angle set Demo")

points = [50,100,200,300,400 ,1000,0,-1000] #[-320, 0, 320, 0, -320/3, -320*2/3, -320, -320-320/3, -320-320*2/3, -2*320]

for i in points:
    print("Set Angle to", i)
    M.setAngle(angle+i)
    time.sleep(2)

time.sleep(1)
M.release()
time.sleep(0.5)

M.setSpeed_PID_P(100) #PID P part
M.setSpeed_PID_I(100) # PID I part
M.setSpeed_PID_I_limit(1000) # PID I integratons limits

print("Speed Demo")
points = [1,2,4,8,10,0,-10,-10]
for i in points:
    print("Set Speed to",i)
    M.setSpeed(i)
    time.sleep(1)

M.release()

print("PWM Demo")

M.setPWM_Limit(500)

points = [200,300,500,0,-300,-400,-500,-250]
for i in points:
    print("Set PWM to",i)
    M.setPWM(i)
    time.sleep(1)
    
M.release()

client.close()



