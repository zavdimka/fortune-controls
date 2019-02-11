from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.constants import Endian
from collections import OrderedDict
import numpy as np
from intelhex import IntelHex16bit
import time

import logging

class ModBusBootLoader():
    MB_ID_REG = 245 #for bootloader version chec
    MB_ID_REG_CURVAL = 1 # bootloader version
    MB_STATE_REG = 246 # state reg
    MB_MAGIC_REG = 257 #reg to unlock write
    MB_MAGIC_WORD = 4570 #value for unlock
    MB_TRANSFER_SIZE_REG = 249 # size for transfer and crc
    MB_WORK_PAGE_REG = 250

    MB_ACTION_REG = 252 #write 1 to erase current page, 2 write data
    MB_PAGE_SIZE = 253  #page size e.g. 1024 or 2048
    MB_PAGE_COUNT = 254 # page count avalible for read\write
    MB_PAGE_START = 248 # page start
    MP_PAGE_OFFSET = 240 # offset in page addres
    MP_SELECTED_PAGE = 241
    MB_START_STREAM = 256

    MB_GOTO_BL = 1023

    MB_ACTION_ERASE = 1
    MB_ACTION_WRITE = 2
    MB_ACTION_BOOT  = 3

    def __init__(self, client, id):
        self.id = id
        self.client = client
        self.mb_id = -1
        self.mb_state = -1
        self.mb_transfer_size = -1
        self.mb_page_size = -1
        self.mb_page_count = -1
        self.mb_page_start = -1
        self.wr_repeat = 3

    def mb_read_int16(self, addres):
        result = self.client.read_holding_registers(addres, 1, unit=self.id)
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big,
                                                     wordorder=Endian.Little)
        return decoder.decode_16bit_uint()

    def go_bootloader(self):
        self.client.write_register(self.MB_GOTO_BL, self.MB_GOTO_BL, unit=self.id)
        time.sleep(0.4)

    def get_target_info(self):
        self.go_bootloader()
        self.mb_id             = self.mb_read_int16(self.MB_ID_REG)
        self.mb_state          = self.mb_read_int16(self.MB_STATE_REG)
        self.mb_transfer_size  = self.mb_read_int16(self.MB_TRANSFER_SIZE_REG)
        self.mb_page_size      = self.mb_read_int16(self.MB_PAGE_SIZE)
        self.mb_page_count     = self.mb_read_int16(self.MB_PAGE_COUNT)
        self.mb_page_start     = self.mb_read_int16(self.MB_PAGE_START)

    def print_info(self):
        logging.info(f"mb id            is {self.mb_id}")
        logging.info(f"mb state         is {self.mb_state}")
        logging.info(f"mb transfer size is {self.mb_transfer_size}")
        logging.info(f"mb page size     is {self.mb_page_size}")
        logging.info(f"mb page count    is {self.mb_page_count}")
        logging.info(f"mb page start    is {self.mb_page_start}")

    def set_current_page(self, page):
        self.client.write_register(self.MP_SELECTED_PAGE , page, unit=self.id)
      #  logging.info(f"set page   to {page:#0x}")

    def set_current_offset(self, offset):
        self.client.write_register(self.MP_PAGE_OFFSET, offset, unit=self.id)
      #  logging.info(f"set offset to {offset:#0x}")

    def read_data_buff(self):
        if self.mb_transfer_size > 0:
            result = self.client.read_holding_registers(self.MB_START_STREAM, self.mb_transfer_size, unit=self.id)
            decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                         byteorder=Endian.Big,
                                                         wordorder=Endian.Little)
            return [decoder.decode_16bit_uint() for i in range(self.mb_transfer_size)]

    def calc_crc(self, buff):
        i = 0
        for k in buff:
            i += k
        return (i & 0xFFFF)

    def read_data_buff_crc(self):
        if self.mb_transfer_size > 0:
            result = self.client.read_holding_registers(self.MB_START_STREAM, self.mb_transfer_size + 1, unit=self.id)
            decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                         byteorder=Endian.Big,
                                                         wordorder=Endian.Little)
            data = [decoder.decode_16bit_uint() for i in range(self.mb_transfer_size+1)]
            if data[-1] == self.calc_crc(data[:-1]):
                return data[:-1]
            else:
                return []

    def erase_page(self, page):
        self.set_current_page(page)
        self.client.write_register(self.MB_ACTION_REG, self.MB_ACTION_ERASE, unit=self.id)
        logging.info(f'Erasing page {page}')

    def update_state(self):
        self.mb_state = self.mb_read_int16(self.MB_STATE_REG)
        if self.mb_state > 0:
            logging.warning(f'state is {self.mb_state}')
        return self.mb_state

    def reset_state(self):
        self.client.write_register(self.MB_STATE_REG, 0, unit=self.id)

    def run_app(self):
        self.client.write_register(self.MB_ACTION_REG, self.MB_ACTION_BOOT, unit=self.id)

    def write_small_buff(self, buff):
        if len(buff) == self.mb_transfer_size:
            self.reset_state() # reset error state
            builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                           wordorder=Endian.Little)

            [builder.add_16bit_uint(i) for i in buff]
            builder.add_16bit_uint(self.calc_crc(buff))
            payload = builder.build()
            #print(payload)
            self.client.write_registers(self.MB_START_STREAM, payload, skip_encode=True, unit=self.id)
            if self.update_state() == 0: #check errors
                self.client.write_register(self.MB_ACTION_REG, self.MB_ACTION_WRITE, unit=self.id)
                if self.update_state() == 0:
                    return True
        return False

    def write_id_speed(self,id,speed):
        data = [0 for i in range(14)]
        data[2]=id | speed<<8
        data[12] = (~data[2])&0xFFFF
        data[13] = 0xFFFF
        while(len(data)<self.mb_transfer_size):
            data.append(0xFFFF)
        self.reset_state()
        self.erase_page(7)
        self.set_current_offset(0)
        self.set_current_page(7)
        self.write_small_buff(data)
        if self.update_state()>0:
            logging.error(f'Error write id and speed {self.mb_state}')


    def write_flash(self,page, buff,check=True):
        if len(buff) % self.mb_transfer_size == 0:
            self.client.write_register(self.MB_MAGIC_REG, self.MB_MAGIC_WORD, unit=self.id)
            i=0
            err= True
            repeat = 0
            while i<len(buff) and err and repeat < self.wr_repeat:
                logging.debug(f'write page {page + i//self.mb_page_size}')
                cpage = page + i//self.mb_page_size
                coffset = i % self.mb_page_size
                self.set_current_page(cpage)
                self.set_current_offset(coffset)
                logging.info(f'set page and offset to {cpage} : {coffset}')
                err = False
                try:
                    err = self.write_small_buff(buff[i:i+self.mb_transfer_size])
                except AttributeError:
                    err = False
                if not err:
                    logging.warning(f'Error write buff')
                if check:
                    d = self.read_data_buff_crc()
                    f = [i for i,k in zip(d, buff[i:i+self.mb_transfer_size]) if i!=k]
                    if len(f)>0 or not err:
                        err = False
                        repeat += 1
                        logging.error(f"page {page + i//self.mb_page_size} offset {i % self.mb_page_size} ")
                        logging.error("Write check error, try again")
                    else:
                        repeat = 0
                if repeat == 0:
                    i += self.mb_transfer_size

            i -= self.mb_transfer_size
            return (err,i)
        return False

    def read_flash(self,page,size):
        i = 0
        data = []
        while i<size:
            self.set_current_page(page + i // self.mb_page_size)
            self.set_current_offset(i % self.mb_page_size)
            data.extend(self.read_data_buff_crc())
            i += self.mb_transfer_size
        return data

    def read_flash_file(self, page, size, filename):
        self.go_bootloader()
        self.get_target_info()
        f = IntelHex16bit()
        data = self.read_flash(page, size)
        startaddr = 0x04000000
        for i,d in zip(range(len(data)),data):
            f[i+startaddr+page*self.mb_page_size] = d
        f.tofile(filename, format = 'hex' )
        return (page,size)

    def write_flash_file(self, filename, check = True):
        self.go_bootloader()
        self.get_target_info()
        self.client.write_register(self.MB_MAGIC_REG, self.MB_MAGIC_WORD, unit=self.id)
        startaddr = 0x04000000
        f = IntelHex16bit(filename)
        minaddr = f.minaddr()
        skip = minaddr - startaddr
        skip = (skip//self.mb_page_size)*self.mb_page_size
        last = f.maxaddr()
        last = last - startaddr
        last = (last//self.mb_page_size + 1)*self.mb_page_size
        spage = skip // self.mb_page_size
        s = last-skip
        d = []
        logging.info(f"skip  {skip}")
        logging.info(f"last  {last}")
        logging.info(f"s     {s}")
        logging.info(f"write {s*2} Bytes")
        logging.info(f"spage {spage}")
        for i in range(s):
            d.append(f[startaddr+i+skip])
        for i in range(s//self.mb_page_size+1):
            self.erase_page(skip//self.mb_page_size+i)
        #print(d)
        return self.write_flash(spage,d,check)

