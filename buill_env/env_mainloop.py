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

import sensor.adxl355_func as adxl
import env_func as env


####################
# Config read


configfile="./env.ini"
conf=configparser.ConfigParser()

if os.path.exists(configfile):
    conf.read(configfile)
else:
    conf.add_section("setting")
    conf.set("setting","dbfile","./env.db")
    conf.set("setting","log","./log/")
    conf.add_section("thingspeak")
    conf.set("thingspeak","APIKEY","JP847SI0ALQLMLY6")
    conf.add_section("period")

#    conf.set("period","totalperiod",str(60*60*10))#sec単位
#    conf.set("period","sampling",str(600))#sec単位
#    conf.set("period","samplingperiod",str(30))#sec単位

    conf.set("period","total_period",str(60))#　total測定時間
    conf.set("period","sampling",str(10))#DB保存間隔
#    conf.set("period","samplingperiod",str(10))# 加速度センサ測定時間
    conf.set("period","thing_sampling",str(25))#　thingspeak upload間隔


    print("make config")
    with open(configfile, 'w') as configfile:
        conf.write(configfile)

TotalPeriod=int( conf.get("period","total_period"))
SamplingPeriod=float( conf.get("period","sampling"))
Thing_sampling=int( conf.get("period","thing_sampling"))

#############
#
# クラウド、DataBaseの設定
#


#thingspeak
fieldlist=["field1","field2","field3","field4","field5","field6"]
thg=thingspeak.thingspeak(conf.get("thingspeak","APIKEY"))
thg.set_field(fieldlist)

#id は変更不可、それ以外を用途に合わせて編集
#idは自動で追加されます


#key={"cnt":"int","time":"text","x":"real","y":"real","z":"real","x_std":"real","y_std":"real","z_std":"real"}
key=[("cnt","int"),("time","text"),("x_rms","real"),("y_rms","real"),("z_rms","real"),("x_std","real"),("y_std","real"),("z_std","real")]


print(conf.get("setting","dbfile"))
db=sql_lib.miyadb(conf.get("setting","dbfile"),key)

#dbの中身を削除するときは先に以下の命令を実行
db.clear()
db.init_table2()

#####################
#
#   測定関数定義
#   　

def rms(data):
    ret=0
    for dd in data:
        ret=ret+dd*dd
    ret=np.sqrt(ret)
    return ret/len(data)



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
    buf_x_rms=0
    buf_y_rms=0
    buf_z_rms=0

    buf_x_std=0
    buf_y_std=0
    buf_z_std=0


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
        if time.time()-pi.t2 > Thing_sampling:
            pi.trig2()

    elif pi.state=="measure1":

        print("*** measure ***")
        filename="test{0}.csv".format(pi.cnt)
        env.ENV_FUNC(filename)
#        adxl.measure(filename,SamplingJikan)
        df=pd.read_csv(filename)
        df.columns=["page","x","y","z"]

        x_std=df["x"].std()
        y_std=df["y"].std()
        z_std=df["z"].std()

        x_rms=rms(df["x"].values)
        y_rms=rms(df["y"].values)
        z_rms=rms(df["z"].values)

        pi.buf_x_rms=x_rms
        pi.buf_y_rms=y_rms
        pi.buf_z_rms=z_rms

        pi.buf_x_std=x_std
        pi.buf_y_std=y_std
        pi.buf_z_std=z_std


        #thing speak
        #いったんコメントアウト
        # datlist=[x_ave,y_ave,z_ave,x_std,y_std,z_std]
        # thg.sendall(datlist)

        #sqlite append
        pi.t1=time.time()
        tm=dt.datetime.now()
        dat=[pi.cnt,tm,x_rms,y_rms,z_rms,x_std,y_std,z_std]
        db.append2(dat)

        #camera
        #fswebcamtest.savepicture(conf.get("setting","log"),pi.cnt)

        pi.cnt=pi.cnt+1
        pi.end_measure()

    elif pi.state=="measure2":

        print("*** measure thing ***")

        #thing speak
        #いったんコメントアウト
        datlist=[pi.buf_x_rms,pi.buf_y_rms,pi.buf_z_rms,pi.buf_x_std,pi.buf_y_std,pi.buf_z_std]
        thg.sendall(datlist)

        #camera
        #fswebcamtest.savepicture(conf.get("setting","log"),pi.cnt)

        pi.end_measure()




# end process
print("end")
