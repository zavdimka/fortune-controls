import sys
sys.path.append('..\..\Lib')

from pymodbus.client.sync import ModbusSerialClient as ModbusClient #initialize a serial RTU client instance
from modbusbootloader import ModBusBootLoader
import time
import argparse
import logging
import coloredlogs

def config_log(level=logging.INFO):
    format = ' '.join([
        '%(asctime)s',
        '%(filename)s:%(lineno)d',
        # '%(threadName)s',
        '%(levelname)s',
        '%(message)s'
    ])
    formatter = logging.Formatter(format)
    logger = logging.getLogger()
    # Remove existing handlers
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    logger.setLevel(level)
    formatter2 = coloredlogs.ColoredFormatter(format)
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(formatter2)
    logger.addHandler(consoleHandler)

config_log()    

parser = argparse.ArgumentParser()

parser.add_argument("action",choices=['r', 'w', 'e', 'i'], type=str.lower, help = "port to connect")
parser.add_argument("port", type=str, default='COM1', help = "port to connect")
parser.add_argument("file", type=str, default='1.hex', help = "file to deal with")
parser.add_argument("-s", "--baund", type=int, default=115200, help = "port speed")
parser.add_argument("-a", "--addr", type=int, default=1, help = "modbus addres")
parser.add_argument("-t", "--timeout", type=float, default=0.8, help = "modbus timeout")
parser.add_argument("-i", "--newid", type=int, default=1, help = "modbus new id")
args = parser.parse_args()

logging.info(f"connecting to port {args.port}")
logging.info(f"boundrate     is   {args.baund}")
logging.info(f"timeout       is   {args.timeout}")

client= ModbusClient(method = "rtu", port=args.port, stopbits = 1,
                     bytesize = 8, parity = 'N', baudrate= args.baund,
                     timeout = args.timeout )

l = ModBusBootLoader(client, args.addr)

logging.info(f"connected ok")

if args.action == 'r':
    l.get_target_info()
    l.print_info()
    t = time.time()
    logging.info("reading flash, it can take few seconds")
    r = l.read_flash_file(8,16*512, args.file) #16 pages of 1024 bytes
    logging.info(f"save to {args.file} {r[1]*2} Bytes in {time.time()-t:.2f} speed {r[1]*2/(time.time()-t):.1f} Bytes/sec")
    l.run_app()

if args.action == 'w':
    l.get_target_info()
    l.print_info()
    t = time.time()
    logging.info("writing flash, it can take few seconds")
    r = l.write_flash_file(args.file)
    logging.info(f"write from{args.file} {r[1]*2} Bytes in {time.time()-t:.2f} speed {r[1]*2/(time.time()-t):.1f} Bytes/sec")
    l.run_app()

if args.action == 'i':
    l.get_target_info()
    l.print_info()
    t = time.time()
    logging.info("set id, it can take few seconds")
    l.write_id_speed(args.newid, 10)
    logging.info(f"set in {time.time()-t:.2f}")
    l.run_app()

client.close()
