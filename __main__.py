# -*- coding: utf-8 -*-
"""
Created on Thu Jan 15 13:20:23 2015

@author: dvalovcin
"""

from PyQt4 import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import threading
from mainWindow_ui import Ui_MainWindow
import datetime
import re
import time
from Oscilloscope import TDSOscilloscope
from KeithleyInstruments import Keithley2400


class Win(QtGui.QMainWindow):
    leakSig = QtCore.pyqtSignal(object)
    oscSig = QtCore.pyqtSignal(object)
    statusSig = QtCore.pyqtSignal(object)
    intSig = QtCore.pyqtSignal(object)

    def __init__(self):
        super(Win,self).__init__()
        self.scope = TDSOscilloscope(GPIB_Number = 'GPIB1::1::INSTR')
        self.keith = Keithley2400(GPIB_Number = 'GPIB1::24::INSTR')
        self.initUI()
        
        self.runFlag = False
        
        self.leakSig.connect(self.updateLeakage)
        self.oscSig.connect(self.updateOsc)
        self.statusSig.connect(self.updateStatusBar)
        self.intSig.connect(self.updateIntegration)
        self.changeChannel(0) #set the first channel
        
        self.leakValues = np.empty((0,2))
        self.intValues = np.empty((0,2))
        self.scopeValues = None
        self.saveLoc = ''
        self.voltage = 0
        
    def initUI(self):
        #Import ui file from designer
        self.ui=Ui_MainWindow()
        self.ui.setupUi(self)  
        
        #Define the plot widgets where data is updated
        self.leakGraph = self.ui.gLeakage.plot()
        plotitem = self.ui.gLeakage.getPlotItem()
        plotitem.setLabel('top',text='Leakage Current')
        plotitem.setLabel('left',text='Current',units='A')
        plotitem.setLabel('bottom',text='voltage', units='V')
        self.oscGraph = self.ui.gOscilloscope.plot()
        plotitem = self.ui.gOscilloscope.getPlotItem()
        plotitem.setLabel('top',text='Waveform')
        plotitem.setLabel('left',text='Voltage',units='V')
        plotitem.setLabel('bottom',text='Time', units='s')
        self.intGraph = self.ui.gValueVsV.plot()
        plotitem = self.ui.gValueVsV.getPlotItem()
        plotitem.setLabel('top',text='Waveform')
        plotitem.setLabel('left',text='Integrated Scope',units='V')
        plotitem.setLabel('bottom',text='Gate Voltage', units='V')
#        self.integrationRegion = pg.LinearRegionItem([0, 1],
#                                                     bounds=[0, 1],
#                                                     brush=pg.mkBrush(QtGui.QColor(0,255,0,50)))
#        self.integrationRegion.setMovable(False)
#        self.ui.gOscilloscope.addItem(self.integrationRegion)
                
        #Connect all the interfaces
        self.ui.bStartScan.clicked.connect(self.startScan)
        self.ui.bAbortScan.clicked.connect(self.abortScan)
        self.ui.bAbortScan.setEnabled(False)
        self.ui.mFileExit.triggered.connect(self.close)
        self.ui.cChannelPicker.currentIndexChanged.connect(self.changeChannel)
        self.ui.mFileUpdate.triggered.connect(self.getScope)
        self.ui.bSaveDirectory.clicked.connect(self.updateSaveLoc)
        self.ui.bResetLeak.clicked.connect(self.resetLeak)
        
#        self.ui.tIntEnd.editingFinished.connect(self.updateLR)
#        self.ui.tIntStart.editingFinished.connect(self.updateLR)
                
        self.show()
        
#    def updateLR(self):
#        self.integrationRegion.setBounds([float(self.ui.tIntStart.text()), float(self.ui.tIntEnd.text())])
        
    def getScope(self):
        self.scope.getScopeValues()
#        self.integrationRegion.setBounds([0, 2500*self.scope.dt])
    def closeEvent(self, event):
        print 'closed'
        self.close()

    def startScan(self):
        #test inputs
        try:
            start = self.parseInp(self.ui.tGateStart.text())
            self.ui.tGateStart.setText(str(start))
            step = self.parseInp(self.ui.tGateStep.text())
            self.ui.tGateStep.setText(str(step))
            end = self.parseInp(self.ui.tGateEnd.text())
            self.ui.tGateEnd.setText(str(end))
            m = self.parseInp(self.ui.tMeasureEvery.text())
            self.measureEvery = int(m)
        except Exception as e:
            self.ui.statusbar.showMessage('Error converting input: {}'.format(e[1]), 3000)
            return
        if (end-start)*step<0:
            self.ui.statusbar.showMessage('Incorrect step size', 3000)
            return
#        if start*end<0:
#            self.ui.statusbar.showMessage('Sorry. Put start/stop on same sign', 3000)
#            return
        #disable all the buttons and inputs so they don't get changed and confuse the user
        self.ui.cChannelPicker.setEnabled(False)
        self.ui.bStartScan.setEnabled(False)
        self.ui.bAbortScan.setEnabled(True)
        self.ui.tGateStart.setEnabled(False)
        self.ui.tGateStep.setEnabled(False)
        self.ui.tGateEnd.setEnabled(False)
        self.ui.tSave.setEnabled(False)
        self.ui.tMeasureEvery.setEnabled(False)
        self.ui.mFileUpdate.setEnabled(False)
        
        #Start the thread to take the data
        self.runFlag = True
        self.scanningThread = threading.Thread(target=self.runScan, args = (start, step, end))
        self.scanningThread.start()
        
    
    def abortScan(self):
        #Re-enable all of the buttons/inputs
        self.ui.cChannelPicker.setEnabled(True)
        self.ui.bStartScan.setEnabled(True)
        self.ui.bAbortScan.setEnabled(False)
        self.ui.tGateStart.setEnabled(True)
        self.ui.tGateStep.setEnabled(True)
        self.ui.tGateEnd.setEnabled(True)
        self.ui.tSave.setEnabled(True)
        self.ui.tMeasureEvery.setEnabled(True)
        self.ui.mFileUpdate.setEnabled(True)
        self.runFlag = False
        try:
            self.statusSig.emit('Aborting...')
            self.scanningThread.join()
        except:
            pass
    
    def parseInp(self, inp):
        ret = None
        #see if we can just turn it into a number and leave if we can
        try:
            ret = float(inp)
            return ret
        except:
            pass
        #tests to see whether digit is whole number or decimal, and if it has 
        #some modifier at the end
        toMatch = re.compile('-?(\d+\.?\d*|\d*\.\d+)(m|u|n)?\Z')
        if re.match(toMatch, inp):
            convDict = {'m': 1e-3, 'u':1e-6, 'n':1e-9}
            try:
                ret = (float(inp[:-1]) * #convert first part to number
                   convDict[[b for b in convDict.keys() if b in inp][0]]) #and multiply by the exponential
                return ret
            except:
                print 'uh oh'
        else:
            raise TypeError('Error with input', str(inp))
            
    def runScan(self, *args):
        start = args[0]
        step = args[1]
        end = args[2]
        voltageRange = np.arange(start, end, step)
        voltageRange = np.append(voltageRange, end)
        
        self.keith.turnOn()
        #Incase things got changed.
        self.scope.getScopeValues()
        
        if not start == 0:
            print 'not equal'
            startStep = step
            if start*step<0:
                startStep = -step
            for voltage in np.arange(0, start, startStep):
                if not self.runFlag:
                    break
                self.doRamp(voltage)
        else:
            print 'equal'
            
        measureCount = self.measureEvery
        
        for voltage in voltageRange:
            #Make sure the main thread didn't abort the run
            if not self.runFlag:
                break
            measureCount = measureCount - 1
            if measureCount == 0 or voltage==voltageRange[0]:
                measureCount = self.measureEvery
                if not self.doMeasurementPoint(voltage):
                    print 'Error: Time out?'
                    continue
            else:
                self.doRamp(voltage)
                    
        
        ###########
        #Uncomment this loop if you want to measure for hysteresis
#        for voltage in voltageRange[::-1]:
#            #Make sure the main thread didn't abort the run
#            if not self.runFlag:
#                break
#            if not self.doMeasurementPoint(voltage, True):
#                break
        
        
        for voltage in np.arange(self.voltage, 0, -abs(step)*np.sign(self.voltage)):
            self.doRamp(voltage)
        
        
            
        self.keith.setVoltage(0)
        self.keith.turnOff()
        self.saveLeakage()
        self.abortScan()
        
    def doRamp(self, voltage):
        self.voltage = voltage
        self.keith.setVoltage(voltage)
        time.sleep(.2)
        self.statusSig.emit('Ramping. Voltage: '+str(voltage))
        
    def doMeasurementPoint(self, voltage, reverse = False):
        self.voltage = voltage
        self.statusSig.emit('Measuring. Voltage: '+str(voltage))
        self.keith.setVoltage(voltage)
        time.sleep(.2) #Sleep incase there's a lag between updating the scope
        #Issues with the scope timing out, so test for it
        self.scope.start_acquire()
        try:
            self.scope.acq_complete()
        except:
            self.statusSig.emit('Error reading from scope (other timeout?)')
            return False
        try:
            self.scope.read_channel(self.oscChannel)
        except:
            self.statusSig.emit('Error reading from scope (timeout?)')
            return False
        
        self.getScope()
        self.scopeValues = self.scope.scaleWaveforms()
#            self.scopeValues = self.scope.wfmDict[self.oscChannel]
        self.time = np.array(range(len(self.scopeValues))) * self.scope.dt
        
        start = self.parseInp(self.ui.tIntStart.text())
        end = self.parseInp(self.ui.tIntEnd.text())
        
        self.leakSig.emit([[voltage, self.keith.readValue()]])
        indexes = (self.time>start)&(self.time<end)
#        indexes = np.array([0 for i in len(self.time) if (i>start and i<end) else 0])
        self.intSig.emit([[voltage, sum(indexes*self.scopeValues)]])
        self.oscSig.emit(np.vstack((self.time, self.scopeValues)).T)
        if reverse:
            self.saveOsc(str(voltage)+'b')
        else:
            self.saveOsc(voltage)
        return True
            
    def updateLeakage(self, data):
        self.leakValues = np.append(self.leakValues, data, axis=0)
        self.leakGraph.setData(self.leakValues[:,0], self.leakValues[:,1])
    
    def updateOsc(self, data):
        self.oscGraph.setData(self.time, self.scopeValues)
    
    def updateIntegration(self, data):
        self.intValues = np.append(self.intValues, data, axis=0)
        self.intGraph.setData(self.intValues[:,0], self.intValues[:,1])
        
    def changeChannel(self, idx):
        self.oscChannel = 'CH'+str(idx+1)
        self.scope.Channel = self.oscChannel
        self.scope.CHA = self.oscChannel
        self.scope.setChannel(self.oscChannel)
        self.scope.getScopeValues()
    
    def saveOsc(self, v):
        baseName = str(self.ui.tSave.text())
        saveName = baseName + str(v)
        
        np.savetxt(self.saveLoc+saveName, np.vstack((self.time, self.scopeValues)).T,
                   header = 'Time(s), Voltage(V)')
        
    def saveLeakage(self):
        np.savetxt(self.saveLoc + str(self.ui.tSave.text())+'Leakage', self.leakValues, header='Voltage(V), Current(A)')
        np.savetxt(self.saveLoc + str(self.ui.tSave.text())+'Integrated', self.intValues, header='BGVoltage(V), SigV*t(V)')
        
        
    def updateSaveLoc(self):
        fname = str(QtGui.QFileDialog.getExistingDirectory(self, "Choose File Directory...",directory=self.saveLoc))
        print 'fname',fname
        if fname == '':
            return
        self.saveLoc = fname + '/'
        
    def resetLeak(self):
        self.leakValues = np.empty((0,2))
        self.leakGraph.setData([],[])
        self.intValues = np.empty((0,2))
        self.intGraph.setData([],[])
    
    def updateStatusBar(self, string):
        self.ui.statusbar.showMessage(string, 3000)
        

def main():
    import sys
    app = QtGui.QApplication(sys.argv)
    ex = Win()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()








































