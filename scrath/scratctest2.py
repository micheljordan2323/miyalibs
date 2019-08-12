
from __future__ import print_function

import datetime as dt
import time
import os
from transitions import Machine

#additional install
import pigpio
#import numpy as np
import configparser
#import pandas as pd


#original
import sys
sys.path.append("../")

import common.sql_lib as sql_lib

import common.thingspeak as thingspeak
#import common.fswebcamtest as fswebcamtest

import sensor.grove_d6t as d6t_lib
import sensor.sht30_lib as sht30
import sensor.omron_2smpd_lib as omron_2smpd_lib

import scratch
import numpy
s=scratch.Scratch(host="192.168.11.28")
#s.connection()
a=0

configfile="./scratch.ini"
conf=configparser.ConfigParser()

if os.path.exists(configfile):
    conf.read(configfile)
else:
    conf.add_section("setting")
    conf.set("setting","D6T_type","8L")
#    conf.set("setting","dbfile","./hotel.db")
#    conf.set("setting","log","./log/")
#    conf.set("setting","camera","yes")
    conf.add_section("thingspeak")
    conf.set("thingspeak","APIKEY","VXI31K2ILAHWUOKS")
    conf.add_section("period")

    conf.set("period","total_period",str(3*60))#sec単位
    conf.set("period","sampling",str(10))#sec単位
#    conf.set("period","thing_sampling",str(30))#sec単位

    print("make config")
    with open(configfile, 'w') as configfile:
        conf.write(configfile)

TotalPeriod=int( conf.get("period","total_period"))
SamplingPeriod=float( conf.get("period","sampling"))
#ThingPeriod=float( conf.get("period","thing_sampling"))




#############
#
# クラウド、DataBaseの設定
#
#thingspeak
# temp,humid,thermo_ave,themo_std,pressure
fieldlist=["field1","field2","field3"]
thg=thingspeak.thingspeak(conf.get("thingspeak","APIKEY"))
thg.set_field(fieldlist)


#############
#
# Sensor
#

sht=sht30.SHT30()
d6t = d6t_lib.GroveD6t("44L")
psensor = omron_2smpd_lib.Grove2smpd02e()




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
print("total")
print(TotalPeriod)
print("sampling")
print(SamplingPeriod)










while True:
    try:
        temp,humid=sht.read()
        press, temp = psensor.readData()

#        a=numpy.random.randint(50)

        s.sensorupdate({"temp":temp})
        s.sensorupdate({"humid":humid})
        s.sensorupdate({"press":press})

        time.sleep(1)
        buf=s.receive()
        print(buf)
#        if buf[0]=="broadcast":
#            print(buf)
        if buf["broadcast"]==["upload"]:
            print("upload func")


    except KeyboardInterrupt:
        print("Disconnected")
        break

s.disconnect()


