import scratch
import time
import numpy

s=scratch.Scratch(host="192.168.11.56")

s.connect()
a=0


while True:
    try:
        a=numpy.random.randint(50)
        s.sensorupdate({"temp":a})
        s.sensorupdate({"detect":"yes"})
        time.sleep(1)
        buf=s.receive()
        if buf[0]=="broadcast":
            print buf[1]


    except KeyboardInterrupt:
        print "Disconnected"
        break

s.disconnect()


