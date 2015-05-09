# -*- coding: utf-8 -*-
"""
Created on Thu Oct 02 09:03:41 2014

@author: dvalovcin
"""

import visa
import numpy as np
import pyqtgraph as pg

class Keithley236:
    on = False
    def __init__(self,GPIB_Number=None):
        rm = visa.ResourceManager()
        self.instrument = rm.get_instrument(GPIB_Number)
        
        pass
        
    def setBias(self,BiasLevel):
        #Set to the desired bias level, auto ranging and waiting 10ms
        toWrite = 'B'+str(BiasLevel)+',0,10X'
        print toWrite
        self.instrument.write('B'+str(BiasLevel)+',0,10X')
        
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
    sourcing = None
    sensing = None
    def __init__(self,GPIB_Number=None,graph = None,stopCurrent=1e-4,compliance=1e-3):
        rm = visa.ResourceManager()
        self.instrument = rm.get_instrument(GPIB_Number)
        if not graph == None:
            self.graphing = True
            self.graph = graph
        else:
            self.graphing = False
            self.graph = None
        self.setScanParams(stopCurrent,compliance)
        
        self.instrument.write("*rst; status:preset; *cls")
        self.setSourceMode('volt')
        self.setSenseMode('curr')
        
        #set sensing ranging
        self.setSenseRange(5e-3)
        self.instrument.write("sens:CURR:prot:lev " + str(compliance)) 
        self.instrument.write("SYST:RSEN OFF") #set to 2point measurement?
        
    def setSourceMode(self, mode):
        newMode = 'volt'
        if mode.lower() in ('c', 'current', 'curr'):
            newMode = 'curr'
        st = 'sour:func:mode '+newMode
        self.instrument.write(st)
        self.sourcing = newMode
    
    def setSenseMode(self, mode):
        newMode = "'volt'"
        if mode.lower() in ('c', 'current', 'curr'):
            newMode = "'curr'"
        st = 'sens:func  '+newMode
        self.instrument.write(st)
        #cut off the leading/tailing quote marks        
        self.sensing = newMode[1:-1]
        
    def setSenseRange(self, level):
        if level>0:
            #turn off autorange
            lev = 'auto off'
            self.write('sens:'+self.sensing+':rang:'+lev)
            #set the range
            lev = 'upp '+ str(level)
            self.write('sens:'+self.sensing+':rang:'+lev)
        else:
            #Turn on autorange if negative number is given
            lev = 'auto on'
            self.write('sens:'+self.sensing+':rang:'+lev)
            
    def setSourceRange(self, level):
        if level>0:
            #turn off autorange
            lev = 'auto off'
            self.write('sour:'+self.sourcing+':rang:'+lev)
            #set the range
            lev = 'upp '+level
            self.write('sour:'+self.sourcing+':rang:'+lev)
        else:
            #Turn on autorange if negative number is given
            lev = 'auto on'
            self.write('sour:'+self.sourcing+':rang:'+lev)
        
    def setCompliance(self, level):
        pass
    
    def set4Probe(self, flag):
        doIt = 'OFF'
        if flag:
            doIt = 'ON'
        
        
        
    def setScanParams(self,stop1,compliance):
        points1 =41   #number of data points
        start1 = 0# mA

        points2 =81   #number of data points
        start2 = stop1# mA
        stop2 = -stop1 # mA  *** SINGLE SCAN ***
        
        points3 =21   #number of d06-10-2014ata points
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
        
        self.instrument.write("sens:curr:prot:lev " + str(compliance)) 
        
    def doScan(self):
        #turn on output
        self.instrument.write("OUTP ON")
        data = np.zeros([self.points,2],float)
        for i in range(0,self.points):
                data[i,0] = self.gainarr[i]
                self.setCurrent(self.gainarr[i])
                data[i,1] = self.readValue()
        self.instrument.write("OUTP OFF")
        return data
    
    def readValue(self):
        ret = self.instrument.ask("read?").encode('ascii')
        #comes back as a unicode, comma separated list of values
        return float(ret.encode('ascii')[:-1].split(',')[1])    
    def setCurrent(self,current):
        self.instrument.write("sour:curr:lev " + str(current))
        
    def setVoltage(self, voltage):
        self.instrument.write('sour:volt:lev ' + str(voltage))
        
    def turnOn(self):
        self.instrument.write('OUTP ON')
    
    def turnOff(self):
        self.instrument.write('OUTP OFF')
        
    def write(self, command):
        self.instrument.write(command)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
        