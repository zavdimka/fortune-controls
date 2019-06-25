import sys
sys.path.append('..\..\Lib')
sys.path.append('../../Lib')

from pymodbus.client.sync import ModbusSerialClient as ModbusClient #initialize a serial RTU client instance
from x4motor import X4Motor
import time
import argparse
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

parser = argparse.ArgumentParser()

parser.add_argument("port", type=str, default='COM1', help = "port to connect")
parser.add_argument("action",choices=['r', 'w', 'e'], type=str.lower, help = "port to connect")
parser.add_argument("file", type=str, default='test.npy', help = "file to deal with")
parser.add_argument("-s", "--baund", type=int, default=115200, help = "port speed")
parser.add_argument("-a", "--addr", type=int, default=1, help = "modbus addres")
parser.add_argument("-t", "--timeout", type=float, default=0.8, help = "modbus timeout")
args = parser.parse_args()

log.info(f"connecting to port {args.port}")
log.info(f"boundrate     is   {args.baund}")
log.info(f"timeout       is   {args.timeout}")

client= ModbusClient(method = "rtu", port=args.port, stopbits = 1,
                     bytesize = 8, parity = 'N', baudrate= args.baund,
                     timeout = args.timeout )

log.info(f"connected ok")


if args.action == 'w':
        M = X4Motor(client, {'id':args.addr})
        M.loadsensorconfig(args.file)
        log.info("load ok")
        M.save2flash()
        log.info('save to flash ok')
        
if args.action == 'r':
        M = X4Motor(client, {'id':args.addr})
        M.savesensorconfig(args.file)
        log.info('read ok')

    

client.close()
