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

import sensor.grove_d6t as d6t_lib


import sensor.sht30_lib as sht30
import sensor.omron_2smpd_lib as omron_2smpd_lib


####################
# Config read

configfile="./hotel.ini"
conf=configparser.ConfigParser()

if os.path.exists(configfile):
    conf.read(configfile)
else:
    conf.add_section("setting")
    conf.set("setting","D6T_type","8L")
    conf.set("setting","dbfile","./hotel.db")
    conf.set("setting","log","./log/")
    conf.set("setting","camera","yes")
    conf.add_section("thingspeak")
    conf.set("thingspeak","APIKEY","L0Z78PQTFYUWIER3")
    conf.add_section("period")

    conf.set("period","total_period",str(3*60))#sec単位
    conf.set("period","sampling",str(5))#sec単位
    conf.set("period","thing_sampling",str(30))#sec単位

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

key = [("cnt","int"),("time","text"),("door","int")]
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

pp = pigpio.pi()
pp.set_mode(17, pigpio.INPUT)
pp.set_pull_up_down(17, pigpio.PUD_DOWN)




#####################
#
#   　ステートマシンで実装



#状態の定義
states = ['init', 'wait', 'd_open','d_close', 'quit']

#遷移の定義
# trigger：遷移の引き金になるイベント、source：トリガーイベントを受ける状態、dest：トリガーイベントを受けた後の状態
# before：遷移前に実施されるコールバック、after：遷移後に実施されるコールバック
transitions = [
    { 'trigger': 'end_init',       'source': 'init',   'dest': 'wait'},

    { 'trigger': 'trig0',  'source': 'wait',  'dest': 'd_open'},
    { 'trigger': 'trig1',  'source': 'wait',  'dest': 'd_close'},


    { 'trigger': 'trig1',  'source': 'd_close',  'dest': 'd_open',"before":"checktime1"},
    { 'trigger': 'timeend',     'source': 'd_close',     'dest': 'quit'},

    { 'trigger': 'trig0',  'source': 'd_open',  'dest': 'd_close',"before":"checktime1"},
    { 'trigger': 'timeend',     'source': 'd_open',     'dest': 'quit'}

]

#状態を管理したいオブジェクトの元となるクラス
# 遷移時やイベント発生時のアクションがある場合は、当クラスのmethodに記載する
class Matter(object):
    t0=0
    t1=0
    t2=0
    cnt=0
    buf_door=0

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

        if pp.read(17)==0:
            pi.trig0()
        if pp.read(17)==1:
            pi.trig1()
        print("wait{0}".format( pp.read(17)))



    elif pi.state=="d_open":
        if pp.read(17)==0:
            pi.t1=time.time()
            tm=dt.datetime.now()
            dat=[pi.cnt,tm,1]
            db.append2(dat)

            pi.t1=time.time()
            tm=dt.datetime.now()
            dat=[pi.cnt,tm,0]
            db.append2(dat)

            pi.trig0()

        if time.time()-pi.t0 > TotalPeriod:
            pi.timeend()



    elif pi.state=="d_close":
        if pp.read(17)==1:
            pi.t1=time.time()
            tm=dt.datetime.now()
            dat=[pi.cnt,tm,0]
            db.append2(dat)

            pi.t1=time.time()
            tm=dt.datetime.now()
            dat=[pi.cnt,tm,1]
            db.append2(dat)


            pi.trig1()


        if time.time()-pi.t0 > TotalPeriod:
            pi.timeend()





        #thing speak
        #datlist=[temp,humid,tpn.mean(),tpn.std(),press]
        #thg.sendall(datlist)

        #key={"cnt":"int","time":"text","temp":"real","humid":"real","th_avez":"real","th_std":"real","pressure":"real","rawdata":"text"}

        #sqlite append



        #camera
        #if conf.get("setting","camera")=="yes":
        #    fswebcamtest.savepicture(conf.get("setting","log"),pi.cnt)

        pi.cnt=pi.cnt+1


    elif pi.state=="measure2":

        print("*** measure2 thing ***")


        #thing speak
        datlist=[1]
        thg.sendall(datlist)

        #camera
        if conf.get("setting","camera")=="yes":
            fswebcamtest.savepicture(conf.get("setting","log"),pi.cnt)

        pi.end_measure()



# end process
print("end")
