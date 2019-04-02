import sys
sys.path.append('..\Lib')

from pymodbus.client.sync import ModbusSerialClient as ModbusClient #initialize a serial RTU client instance
from x4motor import X4Motor
import time
import hjson

client= ModbusClient(method = "rtu", port="/dev/ttyS1", stopbits = 1,
                     bytesize = 8, parity = 'N', baudrate= 115200,
                     timeout = 0.8 )

client.connect()

f = open('config.json')
config = hjson.loads(f.read())
f.close()

M = X4Motor(client, settings = config)

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

print("Speed Demo")
points = [1,2,4,8,10,0,-10,-10]
for i in points:
    print("Set Speed to",i)
    M.setSpeed(i)
    e = M.readError()
    if e>0:
        print("Error is", e)
    time.sleep(1)

M.release()

print("PWM Demo")

M.setPWM_Limit(500)

points = [200,300,500,0,-300,-400,-500,-250]
for i in points:
    print("Set PWM to",i)
    M.setPWM(i)
    e = M.readError()
    if e>0:
        print("Error is", e)
    time.sleep(1)
    
M.release()

client.close()



