# -*- coding: utf-8 -*-
"""
Created on Fri Oct 03 17:03:43 2014

@author: dvalovcin
"""

# -*- coding: utf-8 -*-
"""
Created on Thu Oct 02 09:03:41 2014

@author: dvalovcin
"""

import numpy as np
import pyqtgraph as pg
import time

class fakeInstrument:
    def write(self,string):
        print string
    def ask(self,string):
        a = str(np.random.rand())
        b = str(np.random.rand())
        c = str(np.random.rand())
        return u''+a+','+b+','+c+',1243\n'

class Keithley236:
    on = False
    def __init__(self,GPIB_Number=None):
        self.instrument = fakeInstrument()
        
    def setBias(self,BiasLevel):
        #Set to the desired bias level, auto ranging and waiting 10ms
        toWrite = 'B'+str(BiasLevel)+',0,10X'
        print toWrite
        self.instrument.write('B'+str(BiasLevel)+',0,10X')
        time.sleep(.1)
        
    def askCurrent(self):
        return float(self.instrument.ask('G5,2,0X').encode('ascii')[:-2].split(',')[1])
        
    def toggleOutput(self):
        self.on = not self.on
        toWrite = 'N'+str(int(self.on))
        print toWrite
        self.instrument.write(toWrite)
        
    def turnOff(self):
        self.on = False
        self.instrument.write('N0X')
    
    def turnOn(self):
        self.on = True
        self.instrument.write('N1X')
        
        
        
class Keithley2400:
    def __init__(self,GPIB_Number=None,stopCurrent=1e-4,compliance=1e-3):
        self.instrument = fakeInstrument()
        self.setScanParams(stopCurrent,compliance)
        
        self.instrument.write("*rst; status:preset; *cls")
        self.instrument.write("sour:func:mode volt")
        self.instrument.write("sour:volt 0")
        self.instrument.write("SENS:FUNC 'CURR'")
        self.instrument.write("sens:curr:range:auto off")
        #Set the upper range on the measurement so we can set the compliance
        self.instrument.write("SENS:CURR:RANG:UPP 5e-3")
        if compliance<1e-3:
            print "Compliance cannot be less than 1mV"
            compliance = 1e-3
        self.instrument.write("sens:curr:prot:lev " + str(compliance)) 
        self.instrument.write("SYST:RSEN ON") #set to 2point measurement?
        
    def setScanParams(self,stop1,compliance):
        points1 =21   #number of data points
        start1 = 0# mA

        points2 =41   #number of data points
        start2 = stop1# mA
        stop2 = -stop1 # mA  *** SINGLE SCAN ***
        
        points3 =11   #number of d06-10-2014ata points
        start3 = -stop1# mA
        stop3 = start1 # mA  *** SINGLE SCAN ***
        #END initialization
        
        ## Calculations
        step = (1.0*stop1-1.0*start1)/(points1-1)
        gainarr1 = np.arange(start1,stop1,step)
        gainarr1 = np.append(gainarr1,stop1)
        
        step = (1.0*stop2-1.0*start2)/(points2-1)
        gainarr2= np.arange(start2,stop2,step)
        gainarr2 = np.append(gainarr2,stop2)
        
        step = (1.0*stop3-1.0*start3)/(points3-1)
        gainarr3 = np.arange(start3,stop3,step)
        gainarr3 = np.append(gainarr3,stop3)
        gainarr = np.append(gainarr1, gainarr2)
        self.gainarr = np.append(gainarr, gainarr3)
        ## END calculations06-10-2014
        self.points = points1+points2+points3
        
        self.instrument.write("sens:volt:prot:lev " + str(compliance)) 
        
    def doScan(self):
        #turn on output
        self.instrument.write("OUTP ON")
        data = np.zeros([self.points,2],float)
        for i in range(0,self.points):
                data[i,0] = self.gainarr[i]
                self.setCurrent(self.gainarr[i])
                data[i,1] = self.readValue()+1e1*self.gainarr[i]
        self.instrument.write("OUTP OFF")
        time.sleep(.25)
        return data
    
    def readValue(self):
        ret = self.instrument.ask("read?").encode('ascii')
        #comes back as a unicode, comma separated list of values
        return float(ret.encode('ascii')[:-1].split(',')[0])
    def setCurrent(self,current):
        self.instrument.write("sour:curr:lev " + str(current))
        
    def setVoltage(self, voltage):
        self.instrument.write('sour:volt:lev ' + str(voltage))
        
    def turnOn(self):
        self.instrument.write('OUTP ON')
    
    def turnOff(self):
        self.instrument.write('OUTP OFF')
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
        