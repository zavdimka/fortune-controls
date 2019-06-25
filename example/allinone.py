import sys
sys.path.append('..\Lib')
sys.path.append('../Lib')


from pymodbus.client.sync import ModbusSerialClient as ModbusClient #initialize a serial RTU client instance
from x4motor import X4Motor
import time
import hjson

client= ModbusClient(method = "rtu", port="COM3", stopbits = 1,
                     bytesize = 8, parity = 'N', baudrate= 115200,
                     timeout = 0.8, strict=False )

client.connect()

f = open('config.json')
config = hjson.loads(f.read())
f.close()

M = X4Motor(client, settings = config)

print(M.readAllRO())

print("Angle read Demo")
for i in range(100):
    angle = M.step
    print("Angle is"+str(angle))
    time.sleep(0.1)
    
print("Angle set Demo")
points = [5,10,20,30,40 ,100,0,-100] 
for i in points:
    print("Set Angle to", i)
    M.step = (angle+i)
    e = M.readError()
    if e>0:
        print("Error is", e)
    time.sleep(2)
    
M.release()
time.sleep(0.5)

print("Speed Demo")
points = [1,2,4,8,10,0,-10,-10]
for i in points:
    print("Set Speed to",i)
    M.speed = i
    e = M.readError()
    if e>0:
        print("Error is", e)
    time.sleep(1)

M.release()

print("PWM Demo")
points = list(range(1,100,10)) + list(range(100,-101,-10)) + list(range(-100,1,10))
for i in points:
    print("Set PWM to",i)
    M.pwm = i*3
    e = M.readError()
    if e>0:
        print("Error is", e)
    time.sleep(0.5)
    
M.release()

client.close()



