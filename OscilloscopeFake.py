# -*- coding: utf-8 -*-
"""
Created on Wed Sep 24 14:43:24 2014

@author: dvalovcin
"""

import numpy as np
from PyQt4 import QtGui, QtCore
from scipy.integrate import simps
import time

class TDSOscilloscope():
    ################# set up variables ########################
    #actual instrument handle
    TDS = None
    #Set the two channels to use
    CHA = 'CH1'
    CHB = 'CH2'
    Channel = CHA
    #Voltage scale for channels
    CHAVoltDiv = 1
    CHBVoltDiv = 1
    #voltage offset for channels
    CHAOffset = 0
    CHBOffset = 0
    #time scale and offset
    TimeScale = 1e-3
    TimeOffset = 0
    #Datawidth of waveforms
    DataWidth = 1
    bitsToDiv = 25
    dt = TimeScale/250
    
    #Actual waveforms to be stored
    CHAWfm = [0]
    CHBWfm = [0]
    changeChannel = {CHA: CHB,
                     CHB: CHA}
    #Length of datapoints to read
    readLength = 2500
    #Dictinoary to read waveforms
    wfmDict = {CHA: [None]*readLength,
               CHB: [None]*readLength}
    x = np.array(range(readLength))
    
    def getScopeValues(self):
        #####get all the important values to do data processing
        #Get the voltage scales
        #asks for the voltage scale, encodes it in ascii, strips the '\n' 
        #  and converts to float
        self.CHAVoltDiv = 1.0
        self.CHBVoltDiv = 1.0
    
        self.CHAOffset = 0.0
        self.CHBOffset = 0.0
        self.TimeScale = 1.0
        #250 is a magic number which accounts for the digitization of the time scale. Found online            
        self.dt = self.TimeScale/250
        print 'gotScope'
        
    def changeChannelstoRead(self, CHA, CHB):
        self.CHA = CHA
        self.CHB = CHB
        
        self.changeChannel = {CHA: CHB,
                              CHB: CHA}
    
    
    def __init__(self, manual = False,*args, **kwargs):
        pass
            
    def read_channel(self, channel):
            
        self.wfmDict[self.CHA] = np.sin(self.x/100.)+np.random.rand(len(self.x))
    
    def acq_complete(self):
        time.sleep(1)
    
    def start_acquire(self):
        pass
    
    def read_both_channels(self):
        a = 316
        b = 616-a
        self.wfmDict[self.CHA] = (100+100*np.random.rand())*np.sin(self.x/100.)*([0]*a+[1]*b+[0]*(2500-a-b))+np.random.rand(len(self.x))
#        self.wfmDict[self.CHB] = (100+100*np.random.rand())*np.sin(self.x/100.)+np.random.rand(len(self.x))
        
    def scaleWaveforms(self):
        self.wfmDict[self.CHA] = (np.array(self.wfmDict[self.CHA])/self.bitsToDiv-self.CHAOffset)*self.CHAVoltDiv
        return self.wfmDict[self.CHA]
#        self.wfmDict[self.CHB] = (np.array(self.wfmDict[self.CHB])/self.bitsToDiv-self.CHBOffset)*self.CHBVoltDiv
        
        
    def boxcarIntegrate(self,channel,bidx,sidx):
        '''
        bidx/sidx tuple of (start, stop) indices of the background and signal
        '''
        if channel not in self.wfmDict.keys():
            print 'Not a valid channel, not integrating'
            return
        background = self.integrate(self.wfmDict[channel],*bidx)
        signal = self.integrate(self.wfmDict[channel],*sidx)
        return signal-background
        
    def integrate(self,channel,iidx,eidx):
        return simps(channel[iidx:eidx],dx=self.dt)
        
    def setChannel(self, channel):
        print channel
        
        
























