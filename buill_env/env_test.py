import os
from datetime import datetime
import serial
import time
import csv
import binascii

UNIT16_MAX = 65535

LOOPMAX = 3

def calc_crc(buf, length):
    """
        データの誤りを検出させるために、CRC演算を行います。
        演算方法の詳細はユーザーマニュアルの68pを参照してください
        https://omronfs.omron.com/ja_JP/ecb/products/pdf/CDSC-016A-web1.pdf
    """
    crc = 0xFFFF
    for i in range(length):
        crc = crc ^ buf[i]
        for i in range(8):
            carrayFlag = crc & 1
            crc = crc >> 1
            if (carrayFlag == 1) : 
                crc = crc ^ 0xA001
    crcH = crc >> 8
    crcL = crc & 0x00FF
    return(bytearray([crcL,crcH]))

def makeG(n1, n2):
    n = int(hex(n1) + format(n2, 'x'), 16)
    if n > (UNIT16_MAX / 2):
        n = n - 65536
    return str(n)

if __name__ == '__main__':
    data = ''
    print("start")
    ser = serial.Serial("/dev/ttyUSB0", 115200, serial.EIGHTBITS, serial.PARITY_NONE, timeout = 10)
    command = bytearray([0x52, 0x42, 0x05, 0x00, 0x01, 0x17, 0x51])
    command = command + calc_crc(command, len(command))
    ser.write(command)
    time.sleep(1)
    ret = ser.read(ser.inWaiting())
    
    if ret[7] == 0:
        print("set logger mode")
        command = bytearray([0x52, 0x42, 0x06, 0x00, 0x02, 0x17, 0x51, 0x01])
        command = command + calc_crc(command, len(command))
        ser.write(command)
        time.sleep(1)
        ret = ser.read(ser.inWaiting())
        print("wait 150sec")
        time.sleep(150)
        print("changed logger mode")
    else:
        print("alraedy logger mode")    
    
    time.sleep(1)
    
    cnt = 0
    loop = 1
    timestamp = datetime.now()
    print("loop start")
    while loop <= LOOPMAX:
        try:
            print("start logger")
            command = bytearray([0x52, 0x42, 0x0c, 0x00, 0x02, 0x18, 0x51, 0x01, 0x00, 0x05, 0x01, 0x00, 0x10, 0x00])
            command = command + calc_crc(command, len(command))
            ser.write(command)
            record_datetime = datetime.now()
            time.sleep(1)
            ret = ser.read(ser.inWaiting())
            
            print("wait logger") 
            command = bytearray([0x52, 0x42, 0x05, 0x00, 0x01, 0x19, 0x51])
            command = command + calc_crc(command, len(command))
            ser.write(command)
            time.sleep(1)
            ret = ser.read(ser.inWaiting())
            print(ret[7])
            while ret[7] == 1:
                command = bytearray([0x52, 0x42, 0x05, 0x00, 0x01, 0x19, 0x51])
                command = command + calc_crc(command, len(command))
                ser.write(command)
                time.sleep(1)
                ret = ser.read(ser.inWaiting())
                print(ret[7])
            
            print("finished logger")
            time.sleep(1)
            
            print("get logger data")
            command = bytearray([0x52, 0x42, 0x0b, 0x00, 0x01, 0x3F, 0x50, 0x02, 0x01, 0x01, 0x00, 0x10, 0x00])
            command = command + calc_crc(command, len(command))
            ser.write(command)
            print("wait collect")
            time.sleep(5)
            datacnt = ser.inWaiting()
            data = ser.read(ser.inWaiting())
            
            time.sleep(1)
            print("end collect")
            time.sleep(1)
            print("getted logger data")
            print("div data")
            cnta = 0
            record_file_name_xyz = record_datetime.strftime('%Y%m%d%H%M%S')+'_data_accel_xyz.csv'
            record_time_xyz = record_datetime.strftime('%X')
            f = open(record_file_name_xyz, 'w')
            while cnta < datacnt:
                page = cnta / 237
                if cnta % 237 == 0:
                    cntb = 43
                    while cntb < 235:
                        xx = makeG(data[cnta + cntb + 1], data[cnta + cntb])
                        yy = makeG(data[cnta + cntb + 3], data[cnta + cntb + 2])
                        zz = makeG(data[cnta + cntb + 5], data[cnta + cntb + 4])
                        writer_xyz = csv.writer(f, lineterminator='\n')
                        writer_xyz.writerow([page, xx, yy, zz])
                        cntb += 6
                        
                cnta += 1
            
            print("wait save")
            time.sleep(5)
            f.close()
            print("loopcnt:",loop)
            loop += 1
            time.sleep(1)
            
        except KeyboardInterrupt:
            break
    
    ser.close()
    print("end")


