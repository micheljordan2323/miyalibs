
#global
import datetime as dt
import time
import os

#additional install
import pigpio
import configparser
from transitions import Machine
import numpy as np
import pandas as pd

import sys
sys.path.append("../")

import common.thingspeak as thingspeak
import common.sql_lib as sql_lib
#import common.fswebcamtest




import sensor.ads1015_lib as adc

####################
# Config read

configfile="./power.ini"
conf=configparser.ConfigParser()

if os.path.exists(configfile):
    conf.read(configfile)
else:
    conf.add_section("setting")
    conf.set("setting","dbfile","./power.db")
    conf.set("setting","log","./log/")
    conf.add_section("thingspeak")
    conf.set("thingspeak","APIKEY","VXI31K2ILAHWUOKS")
    conf.add_section("period")

    conf.set("period","totalperiod",str(1*60))#sec単位
    conf.set("period","sampling",str(5))#sec単位
    conf.set("period","renzoku",str(1))
    conf.set("period","thing_sampling",str(60))#　thingspeak upload間隔

    print("make config")
    with open(configfile, 'w') as configfile:
        conf.write(configfile)

TotalPeriod=int( conf.get("period","totalperiod"))
SamplingPeriod=float( conf.get("period","sampling"))
SokuteiPeriod=float( conf.get("period","renzoku"))
Thing_sampling=int( conf.get("period","thing_sampling"))

#############
#
# クラウド、DataBaseの設定
#


#thingspeak
fieldlist=["field7"]
thg=thingspeak.thingspeak("VXI31K2ILAHWUOKS")
thg.set_field(fieldlist)

#id は変更不可、それ以外を用途に合わせて編集
#idは自動で追加されます


key={"cnt":"int","time":"text","current":"real"}
print(conf.get("setting","dbfile"))
db=sql_lib.miyadb(conf.get("setting","dbfile"),key)

#dbの中身を削除するときは先に以下の命令を実行
db.clear()
db.init_table2()

#####################
#
#   測定関数定義
#   　


adc1015=adc.ads1015()



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
    buf_cur=0
    def __init__(self):
        self.t1=time.time()
        self.t2=time.time()
        self.buf_cur=0

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
        if time.time()-pi.t2 > Thing_sampling:
            pi.trig2()

    elif pi.state=="measure1":

        print("*** measure ***")
        filename="test{0}.csv".format(pi.cnt)
        adc1015.measure(filename,3,SokuteiPeriod,0.001)
        df=pd.read_csv(filename)
        df.columns=["x"]
        x_ave=df["x"].mean()
        pi.buf_cur=x_ave

        #thing speak
        #いったんコメントアウト
        datlist=[x_ave]
        thg.sendall(datlist)

        #sqlite append
        pi.t1=time.time()
        tm=dt.datetime.now()
        dat=[pi.cnt,tm,x_ave]
        db.append2(dat)


        #camera
        #fswebcamtest.savepicture(conf.get("setting","log"),pi.cnt)

        pi.cnt=pi.cnt+1
        pi.end_measure()
    elif pi.state=="measure2":

        print("*** measure thing ***")

        #thing speak
        #いったんコメントアウト
        datlist=[pi.buf_cur]
        thg.sendall(datlist)



        #camera
        #fswebcamtest.savepicture(conf.get("setting","log"),pi.cnt)

        pi.end_measure()        

# end process
print("end")
