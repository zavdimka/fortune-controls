import sys
sys.path.append('..\Lib')
sys.path.append('../Lib')

from pymodbus.client.sync import ModbusSerialClient as ModbusClient #initialize a serial RTU client instance
import time
import argparse
import logging
import coloredlogs
from cryptoloader import CrytoLoader,UpdateServer
import argparse
import time
from x4motor import X4Motor
import numpy as np

def make_connection(args):
    logging.info(f"connecting to port {args.port}")
    logging.info(f"baudrate     is   {args.baud}")

    client = ModbusClient(method="rtu", port=args.port, stopbits=1,
                          bytesize=8, parity='N', baudrate=args.baud,
                          timeout=0.25)
    return client

def update_fw(args):
    logging.info(f"Download and update firmware for {args.id} device to {args.fw}")
    client = make_connection(args)
    l = CrytoLoader(client, args.id)
    s = UpdateServer(args.url, l.get_id())
    f = s.get_firmware_bin(args.fw)
    l.upload_bin(f)
    logging.info(f"Download and update finished")
    if args.fr:
        l.run_app()
        logging.info("Run main App")

def list_fw(args):
    logging.info(f"Get List of firmwares for {args.id} device")
    client = make_connection(args)
    l = CrytoLoader(client, args.id)
    s = UpdateServer(args.url, l.get_id())
    w = s.get_firmware_list()
    for i in w:
        logging.info("---------------------------------------")
        logging.info(f"Name -> {i.get('firmware'):10s}")
        logging.info(f"Date -> {time.ctime(i.get('timestamp'))}")
        logging.info(f"Info -> {i.get('description')}")
    if hasattr(args,'fr'):
        l.run_app()
        logging.info("Run main App")

def scan_dev(args):
    logging.info(f"Start scan Modbus devices")
    client = make_connection(args)
    for i in range(1, 240):
        try:
            l = CrytoLoader(client, i)
            logging.info(f"Device with id {i} OK")
            if args.fr:
                l.run_app()
                logging.info("Run main App")
        except Exception as e:
            pass
        if i % 24 == 0:
            logging.info(f"Progress {(i/2.4):.1f}%")
    logging.info(f"Scan finished")


def settings_fw(args):
    logging.info(f"Set new id {args.id_new} for {args.id} device")
    if args.id_new == args.id:
        logging.error(f"Id are the same")
        return
    client = make_connection(args)
    l = CrytoLoader(client, args.id)
    l.set_new_id(args.id_new)
    logging.info("Change done")
    if args.fr:
        l.run_app()
        logging.info("Run main App")

def calibrate_fw(args):
    logging.info(f"Calibrate of {args.id} device")
    client = make_connection(args)
    l = CrytoLoader(client, args.id)
    s = UpdateServer(args.url, l.get_id())
    l.run_app()
    logging.info(f"PWM is {args.pwm}")
    logging.info(f"Delay is {args.delay}")
    logging.info(f"Pints is {args.points}")
    logging.info(f"Turns is {args.turns}")

    time.sleep(0.5)
    ss = {'I_limit' : 5, 'V_min' : 12, 'TimeOut': 500, 'TempShutDown' : 100, 'id' : args.id}
    m = X4Motor(client, settings= ss)

    data = [[], [], []]

    for i in range(args.turns):
        for j in range(args.points):
            m.setmanual(args.pwm, int(j*0x100/args.points))
            time.sleep(args.delay / 1000)
            a = m.readAllRO()
            data[0].append(a.get("A"))
            data[1].append(a.get("B"))
            data[2].append(a.get("C"))
            time.sleep(args.delay / 1000)
            er = m.readError()
            if er:
                logging.info(f"Error {er}")
        logging.info(f"Progress {i/(args.turns*2)*100:.1f}%")

    for i in range(args.turns - 1, -1, -1):
        for j in range(args.points - 1, -1, -1):
            m.setmanual(args.pwm, int(j * 0x100 / args.points))
            time.sleep(args.delay / 1000)
            a = m.readAllRO()
            data[0].append(a.get("A"))
            data[1].append(a.get("B"))
            data[2].append(a.get("C"))
            time.sleep(args.delay / 1000)

        logging.info(f"Progress {100 - i/(args.turns*2)*100:.1f}%")

    m.setMode(m.MODE_NONE)

    d = np.array(data, dtype=np.uint16)

    result = s.get_calibration(d, args.points, args.pwm)
    calib = result.get('data')
    m.write_config(calib.reshape(-1))
    if args.flash:
        m.save2flash()



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


if __name__ == "__main__":
    config_log()
    S_URL = "http://www.motor.opteh.ru/"

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='commands')

    update_group     = subparsers.add_parser('update', help = "Download and flash firmware")
    listfw_group     = subparsers.add_parser('list', help = "List available firmware")
    scan_group       = subparsers.add_parser('scan', help = "Scan Modbus devices")
    settings_group   = subparsers.add_parser('settings', help="Change id or boudrate")
    calibrate_group  = subparsers.add_parser('calibrate', help="Calibrate hall sensors")

    update_group.add_argument("port", type=str, default="COM1", help = "port to connect with controller")
    update_group.add_argument("-b", type=int, default=115200, dest='baud', help = "serial port baudrate")
    update_group.add_argument("-n",type=int, default=1, dest="id", help="ModBus id number")
    update_group.add_argument("-f",type=str, default="", dest="fw", help="Firmware name")
    update_group.add_argument("-r",action='count', dest="fr", help="Run main app after all")
    update_group.add_argument("-w",type=str, default=S_URL, dest="url", help="URL to update server")
    update_group.set_defaults(func = update_fw)

    listfw_group.add_argument("port", type=str, default="COM1", help = "port to connect with controller")
    listfw_group.add_argument("-b", type=int, default=115200, dest='baud', help = "serial port baudrate")
    listfw_group.add_argument("-n",type=int, default=1, dest="id", help="ModBus id number")
    listfw_group.add_argument("-w", type=str, default=S_URL, dest="url", help="URL to update server")
    listfw_group.set_defaults(func = list_fw)

    scan_group.add_argument("port", type=str, default="COM1", help = "port to connect with controller")
    scan_group.add_argument("-b", type=int, default=115200, dest='baud', help = "serial port baudrate")
    scan_group.add_argument("-f",type=str, default="", dest="fw", help="Firmware name")
    scan_group.set_defaults(func = scan_dev)

    settings_group.add_argument("port", type=str, default="COM1", help = "port to connect with controller")
    settings_group.add_argument("-b", type=int, default=115200, dest='baud', help = "serial port baudrate")
    settings_group.add_argument("-n",type=int, default=1, dest="id", help="ModBus id number")
    settings_group.add_argument("-m",type=int, default=1, dest="id_new", help="ModBus new id number")
    settings_group.add_argument("-r",action='count', dest="fr", help="Run main app after all")
    settings_group.set_defaults(func = settings_fw)


    calibrate_group.add_argument("port", type=str, default="COM1", help = "port to connect with controller")
    calibrate_group.add_argument("-b", type=int, default=115200, dest='baud', help = "serial port baudrate")
    calibrate_group.add_argument("-n",type=int, default=1, dest="id", help="ModBus id number")
    calibrate_group.add_argument("-j",type=int, default=32, dest="points", help="Points in one pole")
    calibrate_group.add_argument("-t",type=int, default=15, dest="turns", help="Full turns for test")
    calibrate_group.add_argument("-p",type=int, default=100, dest="pwm", help="PWM to run test")
    calibrate_group.add_argument("-d",type=int, default=50, dest="delay", help="Delay")
    calibrate_group.add_argument("-w", type=str, default=S_URL, dest="url", help="URL to update server")
    calibrate_group.add_argument("-l", action='count', dest="flash", help="Save to flash")
    calibrate_group.set_defaults(func = calibrate_fw)

    options = parser.parse_args()
    options.func(options)
