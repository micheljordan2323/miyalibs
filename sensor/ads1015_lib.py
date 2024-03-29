# Simple demo of continuous ADC conversion mode for channel 0 of the ADS1x15 ADC.
# Author: Tony DiCola
# License: Public Domain
import time

# Import the ADS1x15 module.
import Adafruit_ADS1x15
import numpy as np

# Create an ADS1115 ADC (16-bit) instance.
#adc = Adafruit_ADS1x15.ADS1115()

# Or create an ADS1015 ADC (12-bit) instance.


class ads1015:
    adc=None
    GAIN=None
    def __init__(self):
        self.adc = Adafruit_ADS1x15.ADS1015()
        # Note you can change the I2C address from its default (0x48), and/or the I2C
        # bus by passing in these optional parameters:
        #adc = Adafruit_ADS1x15.ADS1015(address=0x49, busnum=1)

        # Choose a gain of 1 for reading voltages from 0 to 4.09V.
        # Or pick a different gain to change the range of voltages that are read:
        #  - 2/3 = +/-6.144V
        #  -   1 = +/-4.096V
        #  -   2 = +/-2.048V
        #  -   4 = +/-1.024V
        #  -   8 = +/-0.512V
        #  -  16 = +/-0.256V
        # See table 3 in the ADS1015/ADS1115 datasheet for more info on gain.
        self.GAIN = 1
    def measure(self,filename,channel,period,sleep_period):
        # Start continuous ADC conversions on channel 0 using the previously set gain
        # value.  Note you can also pass an optional data_rate parameter, see the simpletest.py
        # example and read_adc function for more infromation.
        self.adc.start_adc(channel, gain=self.GAIN,data_rate=3300)
        # Once continuous ADC conversions are started you can call get_last_result() to
        # retrieve the latest result, or stop_adc() to stop conversions.

        # Note you can also call start_adc_difference() to take continuous differential
        # readings.  See the read_adc_difference() function in differential.py for more
        # information and parameter description.

        # Read channel 0 for 5 seconds and print out its values.
        start = time.time()
        res=[]
        while (time.time() - start) <= period:
            # Read the last ADC conversion value and print it out.
            value = self.adc.get_last_result()
            res.append(value)
            # WARNING! If you try to read any other ADC channel during this continuous
            # conversion (like by calling read_adc again) it will disable the
            # continuous conversion!
            # print('Channel 0: {0}'.format(value))
            # Sleep for half a second.
            #time.sleep(sleep_period)

        # Stop continuous conversion.  After this point you can't get data from get_last_result!
        self.adc.stop_adc()
        res2=np.array(res)
        np.savetxt(filename,res2,delimiter=',')

        return res
    