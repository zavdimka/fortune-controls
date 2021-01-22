from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.constants import Endian
from collections import OrderedDict

import logging
import numpy as np
import pickle
import requests
import binascii
import time
import struct
from io import BytesIO

class CrytoLoader():
    MB_HWO_REG = 245
    MB_STATE_REG = 246
    MB_PACK_NUM_REG = 247
    MB_ID_12BYTES = 250
    MB_STREAM_REG = 262
    MB_GO_APP = 248
    MB_BOUNDRATE_REG = 270
    MB_MBID_REG = 271

    GO_TO_BOOTLOADER = 1023

    HWO_AM_I = [0x1234]

    MB_BLOCK_SIZE = 128
    STATUS_DESC = ["STOP", "RUN", "DONE", "CRC_ERR", "FAIL"]

    def calc_crc(self, buff):
        i = 0
        for k in buff:
            i += k
        return (i & 0xFFFF)

    def __init__(self, client, id):
        self.client = client
        self.id = id
        i = self.read_hwo_am_i()

        if i in range(0,0x1000):
            logging.info(f"Detected runing firmware {i:X}")
            self.jump_2boot()
            time.sleep(0.5)

        i = self.read_hwo_am_i()

        if i in self.HWO_AM_I:
            self.iam = self.HWO_AM_I.index(i)
            logging.info(f"Bootloader version is {self.iam}")
            self.uid = self.read_id()
            self.uids = ''.join(f'{i:02x}' for i in self.uid)
            logging.info(f"CPU id is {self.uids}")
        else:
            logging.error("Can't find device")
            raise IOError


    def mb_read_int16(self, addres):
        result = self.client.read_holding_registers(addres, 1, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        return decoder.decode_16bit_uint()

    def read_hwo_am_i(self):
        return self.mb_read_int16(self.MB_HWO_REG)

    def read_id(self):
        result = self.client.read_holding_registers(self.MB_ID_12BYTES, 6, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        return [decoder.decode_8bit_uint() for i in range(12)]

    def read_status(self):
        return self.mb_read_int16(self.MB_STATE_REG)

    def clear_status(self):
        self.client.write_register(self.MB_STATE_REG, 0, unit=self.id)

    def get_id(self):
        return  self.uids

    def run_app(self):
        logging.info("Jump to App")
        self.client.write_register(self.MB_GO_APP, 1, unit = self.id)

    def push_buffer(self, buff):
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Little)

        [builder.add_8bit_uint(i) for i in buff]
        builder.add_16bit_uint(self.calc_crc(buff))
        payload = builder.build()
        rq = self.client.write_registers(self.MB_STREAM_REG, payload, skip_encode=True, unit=self.id)
        #logging.info(f"Push {binascii.hexlify(buff)}")
        # logging.info(rq.isError())
        if not rq.isError():
            return True
        else:
            logging.warning(f"Can't write stream data")
            return False

    def set_new_id(self, id):
        self.client.write_register(self.MB_MBID_REG, 0, unit=self.id)


    def upload_bin(self, buff):
        i = 0
        t = time.time()
        self.clear_status()
        while i < len(buff):
            ret = 0
            while ret<5 and not self.push_buffer(buff[i:i + self.MB_BLOCK_SIZE]): ret+=1
            if not ret<5:
                logging.error(f"Too many retrying {ret} break")
                return False
            status = self.read_status()
            if status>1:
                logging.info(f"Status is {self.STATUS_DESC[status]}")
                break
            else:
                i+=self.MB_BLOCK_SIZE
        t = time.time()-t
        s = len(buff)/t
        s/= 1024
        logging.info(f"write {len(buff)//1024} KB in {t:.3} sec speed {s:.2} KB\sec")
        return True

    def jump_2boot(self):
        logging.info("Jump to bootloader")
        self.client.write_register(self.GO_TO_BOOTLOADER, self.GO_TO_BOOTLOADER, unit=self.id)


class UpdateServer():
    def __init__(self, serv_url, id):
        self.url = serv_url
        self.id = id
        self.dbcheck = False
        self.check_db()


    def check_db(self):
        r = requests.get(self.url, params = {'id' : self.id, 'action' : 'test'})
        if not 'Notes' in r.headers:
            logging.error(f"Bad response from server ")
            raise IOError

        if 'OK' in r.text:
            self.dbcheck = True
            logging.info("Device id exist on server")
        else:
            logging.error("Can't find id on server")
            raise IOError

    def get_firmware_list(self):
        r = requests.get(self.url, params = {'id' : self.id, 'action' : 'listjson'})
        if not 'Notes' in r.headers:
            logging.error(f"Bad response from server ")
            raise IOError
        self.fwlist = r.json()
        return self.fwlist

    def get_firmware_bin(self, name):
        r = requests.get(self.url, params={'id': self.id, 'action': 'get', 'version' : name})
        if not 'Notes' in r.headers:
            logging.error(f"Bad response from server ")
            raise IOError
        if len(r.content) < 1024:
            raise IOError
        return r.content

    def get_calibration(self, data, points, pwm = None):
        h = {'Content-Type': 'application/octet-stream', 'id' : self.id, 'Shape' : str(data.shape), 'Points' : str(points)}
        if pwm:
            h["PWM"] = str(pwm)

        ar = {'data' : data, 'points' :  points, 'pwm' : pwm}

        logging.info(f"Data shape {data.shape}")
        np_bytes = BytesIO()
        pickle.dump(ar, np_bytes)
        #np.save(np_bytes, :Wq:q, allow_pickle=True)

        r = requests.post(self.url + "4CALIBRATE", data = np_bytes.getvalue(), headers = h)
        if not 'Notes' in r.headers:
            logging.error(f"Bad response from server ")
            raise IOError

        load_bytes = BytesIO(r.content)
        #loaded_np = np.load(load_bytes, allow_pickle=True)
        loaded_np = pickle.load(load_bytes)

        logging.info(f"Notes is {r.headers.get('Notes')}")
        logging.info(f"Get calibration \n{loaded_np}")
        return loaded_np




