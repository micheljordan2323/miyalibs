"""
Usage example for ADXL355 Python library
This example prints on console the current values
of axes on accelerometer
"""
import sys
import time
from adxl_lib import ADXL355  # pylint: disable=wrong-import-position
import pandas as pd
import datetime as dt 

sys.path.append('../lib/')

MeasurePeriod=3  # seconds
#sleeptime = 60-6 #seconds
sleeptime = 1 #seconds

during=5  #seconds


print("Start")

dd=[]

starttime=dt.datetime.now()

device = ADXL355()           # pylint: disable=invalid-name

while (dt.datetime.now()-starttime).seconds < MeasurePeriod:
    time.sleep(sleeptime)
    starttime2=dt.datetime.now()
    while (dt.datetime.now()-starttime2).seconds < during:
        axes = device.get_axes()     # pylint: disable=invalid-name
        #time.sleep(0.0003)
#        axes["time"]=time.now()
        dd.append(axes)

device.close()

df=pd.DataFrame(dd)
df=df*3.9*0.001*0.001     # 2GのScale Factor 3.9uGより
df.to_csv("axdata.txt")
print(df.head(40))
print("number")
print(len(df))
print("sampling rate  num/s")
print(len(df)/during)
