import datetime as dt
import time
import thingspeak
import pigpio
#import cv2
import sql_lib
import numpy as np
#import fswebcamtest
import configparser
import os
from transitions import Machine
import numpy as np
import pandas as pd

import grove_d6t_copy
import sht30class
import fswebcamtest
import omron2smpdlib

####################
# Config read

configfile="./hotel.ini"
conf=configparser.ConfigParser()

if os.path.exists(configfile):
    conf.read(configfile)
else:
    conf.add_section("setting")
    conf.set("setting","dbfile","./hotel.db")
    conf.set("setting","log","./log/")
    conf.set("setting","camera","yes")
    conf.add_section("thingspeak")
    conf.set("thingspeak","APIKEY","L0Z78PQTFYUWIER3")
    conf.add_section("period")


    conf.set("period","totalperiod",str(30*60))#sec単位
    conf.set("period","sampling",str(60))#sec単位
    print("make config")
    with open(configfile, 'w') as configfile:
        conf.write(configfile)

TotalPeriod=int( conf.get("period","totalperiod"))
SamplingPeriod=float( conf.get("period","sampling"))

#############
#
# クラウド、DataBaseの設定
#


#thingspeak
# temp,humid,thermo_ave,themo_std,pressure
fieldlist=["field1","field2","field3","field4","field5"]
thg=thingspeak.thingspeak("L0Z78PQTFYUWIER3")
thg.set_field(fieldlist)

#id は変更不可、それ以外を用途に合わせて編集
#idは自動で追加されます

key = [("cnt","int"),("time","text"),("temp","real"),("humid","real"),("th_ave","real"),("th_std","real"),("pressure","real"),("rawdata","text")]
#key={"cnt":"int","time":"text","temp":"real","humid":"real","th_avez":"real","th_std":"real","pressure":"real","rawdata":"text"}
print(conf.get("setting","dbfile"))
db=sql_lib.miyadb(conf.get("setting","dbfile"),key)

#dbの中身を削除するときは先に以下の命令を実行
db.clear()
db.init_table2()

#####################
#
#   測定関数定義
#   　
#SH30 temperature
sht=sht30class.SHT30()

#omron d6t
d6t = grove_d6t_copy.GroveD6t()

#omron pressure
psensor = omron2smpdlib.Grove2smpd02e()





#####################
#
#   　ステートマシンで実装



#状態の定義
states = ['init', 'wait', 'measure', 'quit']

#遷移の定義
# trigger：遷移の引き金になるイベント、source：トリガーイベントを受ける状態、dest：トリガーイベントを受けた後の状態
# before：遷移前に実施されるコールバック、after：遷移後に実施されるコールバック
transitions = [
    { 'trigger': 'end_init',       'source': 'init',   'dest': 'wait','before': 'checktime'},
    { 'trigger': 'trig',  'source': 'wait',  'dest': 'measure','before': 'checktime'},
    { 'trigger': 'end_measure',  'source': 'measure',   'dest': 'wait','before': 'checktime'},
    { 'trigger': 'timeend',     'source': 'wait',     'dest': 'quit'}
]

#状態を管理したいオブジェクトの元となるクラス
# 遷移時やイベント発生時のアクションがある場合は、当クラスのmethodに記載する
class Matter(object):
    t0=0
    t1=0
    cnt=0
    def checktime(self):
        self.t1=time.time()
        print(self.state)


pi = Matter()
machine = Machine(model=pi, states=states, transitions=transitions, initial='init', auto_transitions=False)

#####################
#
#   メインループ



pi.t0=time.time()

while pi.state != "quit":
    if pi.state == "init":

        pi.end_init()
    elif pi.state=="wait":

        if time.time()-pi.t0 > TotalPeriod:
            pi.timeend()
        if time.time()-pi.t1 > SamplingPeriod:
            pi.trig()

    elif pi.state=="measure":

        print("*** measure ***")

        temp,humid=sht.read()
        press, temp = psensor.readData()
        try:
                time.sleep(1.0)
                d6t.reopen()
                tpn0, tptat = d6t.readData()
                d6t.close()
                if tpn0 == None:
                        tptat=[0,0,0,0,0,0,0,0,0,0]
        except IOError:
                print("IOError")
        

        tpn=np.array(tpn0)

        #thing speak
        #datlist=[temp,humid,tpn.mean(),tpn.std(),press]
        #thg.sendall(datlist)

        key={"cnt":"int","time":"text","temp":"real","humid":"real","th_avez":"real","th_std":"real","pressure":"real","rawdata":"text"}

        #sqlite append
        pi.t1=time.time()
        tm=dt.datetime.now()
        dat=[pi.cnt,tm,temp,humid,tpn.mean(),tpn.std(),press,",".join([str(rr) for rr in tpn]) ]
        db.append2(dat)


        #camera
        if conf.get("setting","camera")=="yes":
            fswebcamtest.savepicture(conf.get("setting","log"),pi.cnt)

        pi.cnt=pi.cnt+1
        pi.end_measure()

# end process
print("end")
