import datetime as dt
import time
import os
from transitions import Machine


#additional install
import pigpio
import numpy as np
import configparser
import pandas as pd


#original
import sys
sys.path.append("../")

import common.sql_lib as sql_lib

import common.thingspeak as thingspeak
import common.fswebcamtest as fswebcamtest

import sensor.grove_d6t32_temp as d6t_lib


#import sensor.sht30_lib as sht30
#import sensor.omron_2smpd_lib as omron_2smpd_lib


####################
# Config read

configfile="./hotel32_temp.ini"
conf=configparser.ConfigParser()

if os.path.exists(configfile):
    conf.read(configfile)
else:
    conf.add_section("setting")
    conf.set("setting","D6T_type","32L")
    conf.set("setting","dbfile","./hotel32.db")
    conf.set("setting","log","./log/")
    conf.set("setting","camera","yes")
    conf.add_section("thingspeak")
    conf.set("thingspeak","APIKEY","L0Z78PQTFYUWIER3")
    conf.add_section("period")

    conf.set("period","total_period",str(3*60))#sec単位
    conf.set("period","sampling",str(0.5))#sec単位
    conf.set("period","thing_sampling",str(70))#sec単位

    print("make config")
    with open(configfile, 'w') as configfile:
        conf.write(configfile)

TotalPeriod=int( conf.get("period","total_period"))
SamplingPeriod=float( conf.get("period","sampling"))
ThingPeriod=float( conf.get("period","thing_sampling"))


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

key = [("cnt","int"),("time","text"),("th_ave","real"),("th_std","real"),("rawdata","text")]
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
#sht=sht30.SHT30()

#omron d6t

d6t = d6t_lib.GroveD6t(conf.get("setting","D6T_type"))
d6t.reopen()
d6t.init_d6t()

#omron pressure
#psensor = omron_2smpd_lib.Grove2smpd02e()





#####################
#
#   　ステートマシンで実装



#状態の定義
states = ['init', 'wait', 'measure1','measure2', 'quit']

#遷移の定義
# trigger：遷移の引き金になるイベント、source：トリガーイベントを受ける状態、dest：トリガーイベントを受けた後の状態
# before：遷移前に実施されるコールバック、after：遷移後に実施されるコールバック
transitions = [
    { 'trigger': 'end_init',       'source': 'init',   'dest': 'wait'},

    { 'trigger': 'trig1',  'source': 'wait',  'dest': 'measure1','before': 'checktime1'},
    { 'trigger': 'end_measure',  'source': 'measure1',   'dest': 'wait','before': 'checktime1'},

    { 'trigger': 'trig2',  'source': 'wait',  'dest': 'measure2','before': 'checktime2'},
    { 'trigger': 'end_measure',  'source': 'measure2',   'dest': 'wait','before': 'checktime2'},

    { 'trigger': 'timeend',     'source': 'wait',     'dest': 'quit'}
]

#状態を管理したいオブジェクトの元となるクラス
# 遷移時やイベント発生時のアクションがある場合は、当クラスのmethodに記載する
class Matter(object):
    t0=0
    t1=0
    t2=0
    cnt=0
    def __init__(self):
        self.t1=time.time()
        self.t2=time.time()

    def checktime1(self):
        self.t1=time.time()
        print(self.state)
    def checktime2(self):
        self.t2=time.time()
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
            pi.trig1()
        if time.time()-pi.t2 > ThingPeriod:
            pi.trig2()


    elif pi.state=="measure1":

        print("*** measure ***")

#        temp,humid=sht.read()
#        press, temp = psensor.readData()
        tpn0=None
        d6t.reopen()
        time.sleep(0.1)
        tpn0, tptat = d6t.readData2()
        d6t.close()


        if tpn0 != None:
            #thing speak
            #datlist=[temp,humid,tpn.mean(),tpn.std(),press]
            #thg.sendall(datlist)

            key={"cnt":"int","time":"text","th_avez":"real","th_std":"real","rawdata":"text"}

            #sqlite append
            pi.t1=time.time()
            tm=dt.datetime.now()
            tpn=np.array(tpn0)

#           Data save to csv
#            filename="test{0}.csv".format(pi.cnt)
#            f=open(filename,"wb")
#            np.savetxt(f,tpn,delimiter=',',fmt="%.5f")
#            f.close()


            try:
                tpn=np.array(tpn0)
                if len(tpn)>0:
                    dat=[pi.cnt,tm,tpn.mean(),tpn.std(),",".join([str(rr) for rr in tpn]) ]
                    db.append2(dat)
                    pi.buf_tpn=[tpn.mean(),tpn.std()]
            except:
                print("error tpn")


        #camera
        #if conf.get("setting","camera")=="yes":
        #    fswebcamtest.savepicture(conf.get("setting","log"),pi.cnt)

        pi.cnt=pi.cnt+1
        pi.end_measure()


    elif pi.state=="measure2":

        print("*** measure2 thing ***")

                
        tpn=np.array(pi.buf_tpn)

        #thing speak
        datlist=[tpn.mean(),tpn.std()]
        thg.sendall(datlist)

        #camera
        if conf.get("setting","camera")=="yes":
            fswebcamtest.savepicture(conf.get("setting","log"),pi.cnt)

        pi.end_measure()



# end process
print("end")
