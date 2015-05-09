# -*- coding: utf-8 -*-
"""
Created on Wed Sep 24 14:43:24 2014

@author: dvalovcin
"""

import numpy as np
from scipy.integrate import simps
import visa

class TDSOscilloscope:
    ################# set up variables ########################
    #actual instrument handle
    TDS = None
    #Set the two channels to use
    CHA = 'CH1'
    CHB = 'CH2'
    Channel = CHA
    #Voltage scale for channels
    CHAVoltDiv = None
    CHBVoltDiv = None
    #voltage offset for channels
    CHAOffset = None
    CHBOffset = None
    #time scale and offset
    TimeScale = None
    TimeOffset = None
    #Datawidth of waveforms
    DataWidth = 1
    #a scale factor which converts the bits from the 'curve?' command to divisions
    #I don't know where it comes from, I found it online.   
    bitsToDiv = 25.6
    
    #Actual waveforms to be stored
    CHAWfm = [0]
    CHBWfm = [0]
    #Easy dictionary to toggle between the two channels
    changeChannel = {CHA: CHB,
                     CHB: CHA}
    #Length of datapoints to read
    readLength = 2500
    #Dictinoary to read waveforms
    wfmDict = {CHA: [None]*readLength,
               CHB: [None]*readLength}
    
    
    def __init__(self,manual=False,*args, **kwargs):
        rm = visa.ResourceManager();
        if 'GPIB_Number' not in kwargs:
            #Take the first resource that has GPIB in the name
            try:
                GPIB_Number = filter(lambda x: 'GPIB' in x, rm.list_resources())[0]
            except:
                print 'Could not find a GPIB connected'
        else:
            GPIB_Number = kwargs['GPIB_Number']
        try:
            self.TDS = rm.get_instrument(GPIB_Number, timeout = 16000)
        except: 
            raise IOError('Could not find GPIB')
        if manual:
            # Do all the things to set oscilliscope
            pass
        else:
            self.getScopeValues()
        
        ##### Set the acquire mode to one sequence to synchronize
        self.TDS.write('ACQUIRE:STOPAFTER SEQUENCE')
        # Set the data encoding to binary for speed
        self.TDS.write('DATA:ENCDG RIBINARY')
        self.TDS.write('DATA:WID 1')
        print self.TDS.timeout
        
    def changeChannelstoRead(self, CHA, CHB):
        #Swap what is the current channel to read
        if self.Channel==self.CHA:
            self.Channel = CHA
        else:
            self.Channel == CHB
        self.CHA = CHA
        self.CHB = CHB
        
        self.changeChannel = {CHA: CHB,
                              CHB: CHA}
        
        
    def getScopeValues(self):
        #####get all the important values to do data processing
        #Get the voltage scales
        #asks for the voltage scale, encodes it in ascii, strips the '\n' 
        #  and converts to float
        self.CHAVoltDiv = float(self.TDS.ask(self.CHA+':SCALE?').encode('ascii')[:-1])
        self.CHBVoltDiv = float(self.TDS.ask(self.CHB+':SCALE?').encode('ascii')[:-1])
    
        self.CHAOffset = float(self.TDS.ask(self.CHA+':POSITION?').encode('ascii')[:-1])
        self.CHBOffset = float(self.TDS.ask(self.CHB+':POSITION?').encode('ascii')[:-1])
        self.TimeScale = float(self.TDS.ask('HORIZONTAL:SCALE?').encode('ascii')[:-1])
        #250 is a magic number which accounts for the digitization of the time scale. Found online            
        self.dt = self.TimeScale/250
            
            
    def read_channel(self, channel):
        #Read the channel immediately if already datasource
        if channel == self.Channel:
            #datatype specifies that the datawidth is 1 byte
            values = []
            values = self.TDS.query_binary_values('curve?',datatype='b')
            print 'reading channel1', channel
        #Otherwise, must set correct datasoure
        else:
            print 'reading channel2', channel
            self.TDS.write('DATA:SOURCE '+channel)
            self.Channel=channel
            values = self.TDS.query_binary_values('curve?',datatype='b')
        self.wfmDict[channel] = values
        print 'source?', self.TDS.ask('DATA:SOURCE?')
        if channel == self.CHA:
            self.CHAWfm = values
        elif channel == self.CHB:
            self.CHBWfm = values
        else:
            print 'dun goofed, requested channel isn\'t a set channel'
            
    def read_both_channels(self):
        #Already on self.Channel, so read it
        print 'About to read channl {}'.format(self.Channel)
        try:
            self.wfmDict[self.Channel] = self.TDS.query_binary_values('curve?',datatype='b')
        except:
            print "didn't work"
        else:
            pass
        #Change the currently reading channel
        self.Channel = self.changeChannel[self.Channel]
        
        #Read the other channel
        print 'About to change to channel {}'.format(self.Channel)
        self.TDS.write('DATA:SOURCE ' + self.Channel)
        self.wfmDict[self.Channel] = self.TDS.query_binary_values('curve?',datatype='b')
        print 'channel read'
        return True
        
        
    def start_acquire(self):
        #Tell the scope to acquire one set of data
        self.TDS.write('ACQUIRE:STATE RUN')
    
    def stop_acquire(self):
        #Tell the scope to stop collecting
        self.TDS.write('ACQUIRE:STATE STOP')
        
    def acq_complete(self):
        #Query the scope if it has finished collection
        return self.TDS.ask('*OPC?').encode('ascii')[:-1]=='1'
        
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
        self.TDS.write('DATA:SOURCE '+channel)
























