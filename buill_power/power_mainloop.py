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

import ads1015_func as adc

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
    print("make config")
    with open(configfile, 'w') as configfile:
        conf.write(configfile)

TotalPeriod=int( conf.get("period","totalperiod"))
SamplingPeriod=float( conf.get("period","sampling"))
SokuteiPeriod=float( conf.get("period","renzoku"))

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
        filename="test{0}.csv".format(pi.cnt)
        adc1015.measure(filename,3,SokuteiPeriod,0.01)
        df=pd.read_csv(filename)
        df.columns=["x"]
        x_ave=df["x"].mean()

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

# end process
print("end")
