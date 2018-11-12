import sys
sys.path.append('..\..\Lib')

from pymodbus.client.sync import ModbusSerialClient as ModbusClient #initialize a serial RTU client instance
from modbusbootloader import ModBusBootLoader
import time
import argparse
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

parser = argparse.ArgumentParser()

parser.add_argument("action",choices=['r', 'w', 'e', 'i'], type=str.lower, help = "port to connect")
parser.add_argument("port", type=str, default='COM1', help = "port to connect")
parser.add_argument("file", type=str, default='1.hex', help = "file to deal with")
parser.add_argument("-s", "--baund", type=int, default=115200, help = "port speed")
parser.add_argument("-a", "--addr", type=int, default=1, help = "modbus addres")
parser.add_argument("-t", "--timeout", type=float, default=0.8, help = "modbus timeout")
parser.add_argument("-i", "--newid", type=int, default=1, help = "modbus new id")
args = parser.parse_args()

log.info(f"connecting to port {args.port}")
log.info(f"boundrate     is   {args.baund}")
log.info(f"timeout       is   {args.timeout}")

client= ModbusClient(method = "rtu", port=args.port, stopbits = 1,
                     bytesize = 8, parity = 'N', baudrate= args.baund,
                     timeout = args.timeout )

l = ModBusBootLoader(client, args.addr)

log.info(f"connected ok")

if args.action == 'r':
    l.get_target_info()
    l.print_info()
    t = time.time()
    log.info("reading flash, it can take few seconds")
    r = l.read_flash_file(8,16*512, args.file) #16 pages of 1024 bytes
    log.info(f"save to {args.file} {r[1]*2} Bytes in {time.time()-t:.2f} speed {r[1]*2/(time.time()-t):.1f} Bytes/sec")
    l.run_app()

if args.action == 'w':
    l.get_target_info()
    l.print_info()
    t = time.time()
    log.info("writing flash, it can take few seconds")
    r = l.write_flash_file(args.file)
    log.info(f"write from{args.file} {r[1]*2} Bytes in {time.time()-t:.2f} speed {r[1]*2/(time.time()-t):.1f} Bytes/sec")
    l.run_app()

if args.action == 'i':
    l.get_target_info()
    l.print_info()
    t = time.time()
    log.info("set id, it can take few seconds")
    l.write_id_speed(args.newid, 10)
    log.info(f"set in {time.time()-t:.2f}")
    l.run_app()

client.close()
