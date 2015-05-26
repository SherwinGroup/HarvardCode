# -*- coding: utf-8 -*-
"""
Created on Thu Jan 15 13:20:23 2015

@author: dvalovcin
"""

from PyQt4 import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import threading
from mainWindowV2_ui import Ui_MainWindow
import datetime
import re
import time
from InstsAndQt.Instruments import Agilent6000, Keithley2400Instr
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class Win(QtGui.QMainWindow):
    leakSig = QtCore.pyqtSignal(object)
    oscSig = QtCore.pyqtSignal(object)
    statusSig = QtCore.pyqtSignal(object)
    intSig = QtCore.pyqtSignal(object)

    def __init__(self):
        super(Win,self).__init__()
        self.initUI()
        
        self.runFlag = False
        
        self.leakSig.connect(self.updateLeakage)
        self.oscSig.connect(self.updateOsc)
        self.statusSig.connect(self.updateStatusBar)
        self.intSig.connect(self.updateIntegration)
        # self.changeChannel(0) #set the first channel
        
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
        # self.oscGraph = self.ui.gOscilloscope.plot()
        # plotitem = self.ui.gOscilloscope.getPlotItem()
        # plotitem.setLabel('top',text='Waveform')
        # plotitem.setLabel('left',text='Voltage',units='V')
        # plotitem.setLabel('bottom',text='Time', units='s')

        self.ui.gOscilloscope.setXLabel("Time", "s")
        self.ui.gOscilloscope.setY1Label("Signal", "V")
        self.ui.gOscilloscope.setY2Label("Ref", "V")

        bgCol = pg.mkBrush(QtGui.QColor(255, 0, 0, 50))
        sgCol = pg.mkBrush(QtGui.QColor(0, 255, 0, 50))
        self.lrSig = pg.LinearRegionItem(brush = sgCol)
        self.lrBg  = pg.LinearRegionItem(brush = bgCol)
        self.ui.gOscilloscope.plotItem1.addItem(self.lrSig)
        self.ui.gOscilloscope.plotItem1.addItem(self.lrBg)



        self.intGraph = self.ui.gValueVsV.plot()
        plotitem = self.ui.gValueVsV.getPlotItem()
        plotitem.setLabel('top',text='Waveform')
        plotitem.setLabel('left',text='Integrated Scope',units='V')
        plotitem.setLabel('bottom',text='Gate Voltage', units='V')

        try:
            import visa
            rm = visa.ResourceManager()
            gpibList = [i.encode('ascii') for i in rm.list_resources()]
        except Exception as e:
            print "VISA Error:", e
            gpibList = ['a', 'b', 'c']


        # Add the items to the list and make them fake
        gpibList.append("Fake")
        self.ui.cOscGPIB.addItems(gpibList)
        self.ui.cOscGPIB.setCurrentIndex(len(gpibList)-1)
        self.ui.cKeithGPIB.addItems(gpibList)
        self.ui.cKeithGPIB.setCurrentIndex(len(gpibList)-1)

        self.ui.cOscGPIB.currentIndexChanged.connect(self.openOsc)
        self.ui.cKeithGPIB.currentIndexChanged.connect(self.openKeith)


                
        #Connect all the interfaces
        self.ui.bStartScan.clicked.connect(self.startScan)
        self.ui.bAbortScan.clicked.connect(self.abortScan)
        self.ui.bAbortScan.setEnabled(False)
        self.ui.cChannelPicker.currentIndexChanged.connect(self.changeChannel)
        self.ui.bSaveDirectory.clicked.connect(self.updateSaveLoc)
        # self.ui.bResetLeak.clicked.connect(self.resetLeak)
        
#        self.ui.tIntEnd.editingFinished.connect(self.updateLR)
#        self.ui.tIntStart.editingFinished.connect(self.updateLR)
                
        self.show()
        
#    def updateLR(self):
#        self.integrationRegion.setBounds([float(self.ui.tIntStart.text()), float(self.ui.tIntEnd.text())])

    def openOsc(self, GPIB = None):
        if GPIB is None:
            GPIB = str(self.ui.cOscGPIB.currentText())
        try:
            self.scope.close()
        except:
            pass

        # Disconnect to prevent recursions when you redo this
        self.ui.cOscGPIB.currentIndexChanged.disconnect(self.openOsc)
        try:
            self.scope = Agilent6000(GPIB)
            newIdx = self.ui.cOscGPIB.findText(GPIB)
            if newIdx == -1: # Error finding it
                print "ERROR UPDATING OSC GPIB, wanted", GPIB
            else:
                self.ui.cOscGPIB.setCurrentIndex(newIdx)
        except Exception as e:
            print "Error opening Osc"
            self.scope = Agilent6000("Fake")
            self.ui.cOscGPIB.setCurrentIndex(self.ui.cOscGPIB.count()-1)

        self.ui.cOscGPIB.currentIndexChanged.connect(self.openOsc)

    def openKeith(self, GPIB = None):
        if GPIB is None:
            GPIB = str(self.ui.cKeithGPIB.currentText())
        try:
            self.keith.close()
        except:
            pass

        # Disconnect to prevent recursions when you redo this
        self.ui.cKeithGPIB.currentIndexChanged.disconnect(self.openKeith)
        try:
            self.keith = Keithley2400Instr(GPIB)
            newIdx = self.ui.cKeithGPIB.findText(GPIB)
            if newIdx == -1: # Error finding it
                print "ERROR UPDATING KETIH GPIB, wanted", GPIB
            else:
                self.ui.cKeithGPIB.setCurrentIndex(newIdx)
        except Exception as e:
            print "Error opening KETIH"
            self.keith = Keithley2400Instr("Fake")
            self.ui.cKeithGPIB.setCurrentIndex(self.ui.cKeithGPIB.count()-1)

        self.ui.cOscGPIB.currentIndexChanged.connect(self.openKeith)
        
    def getScope(self):
        self.scope.getScopeValues()
#        self.integrationRegion.setBounds([0, 2500*self.scope.dt])
    def closeEvent(self, event):
        print 'closed'
        self.close()

    def startScan(self):
        #test inputs
        start = self.ui.tGateStart.value()
        step = self.ui.tGateStep.value()
        end = self.ui.tGateEnd.value()

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
        except Exception as e:
            print "error in abortion,", e
            
    def runScan(self, *args):
        start = args[0]
        step = args[1]
        end = args[2]

        try:
            self.keith.doLoop(start, end, step, toCall=self.doMeasurementPoint)
        except AssertionError:
            print "Error: Invalid scan parameters"
            self.abortScan()
            return
        except Exception as E:
            print "Error running loop", E
            self.abortScan()
            return

        self.saveLeakage()
        self.abortScan()

        # self.keith.turnOn()
        # #Incase things got changed.
        # self.scope.getScopeValues()
        #
        # if not start == 0:
        #     print 'not equal'
        #     startStep = step
        #     if start*step<0:
        #         startStep = -step
        #     for voltage in np.arange(0, start, startStep):
        #         if not self.runFlag:
        #             break
        #         self.doRamp(voltage)
        # else:
        #     print 'equal'
        #
        # measureCount = self.measureEvery
        #
        # for voltage in voltageRange:
        #     #Make sure the main thread didn't abort the run
        #     if not self.runFlag:
        #         break
        #     measureCount = measureCount - 1
        #     if measureCount == 0 or voltage==voltageRange[0]:
        #         measureCount = self.measureEvery
        #         if not self.doMeasurementPoint(voltage):
        #             print 'Error: Time out?'
        #             continue
        #     else:
        #         self.doRamp(voltage)
        #
        # for voltage in np.arange(self.voltage, 0, -abs(step)*np.sign(self.voltage)):
        #     self.doRamp(voltage)
        #
        #
        #
        # self.keith.setVoltage(0)
        # self.keith.turnOff()
        # self.saveLeakage()
        # self.abortScan()
        
    def doMeasurementPoint(self, voltage, reverse = False):
        self.voltage = voltage
        self.statusSig.emit('Measuring. Voltage: '+str(voltage))
        # self.keith.setVoltage(voltage)
        # time.sleep(.2) #Sleep incase there's a lag between updating the scope
        # #Issues with the scope timing out, so test for it
        # self.scope.start_acquire()
        # try:
        #     self.scope.acq_complete()
        # except:
        #     self.statusSig.emit('Error reading from scope (other timeout?)')
        #     return False
        # try:
        #     self.scope.read_channel(self.oscChannel)
        # except:
        #     self.statusSig.emit('Error reading from scope (timeout?)')
        #     return False
        #
        # self.getScope()

        Sig, Ref = self.scope.getMultipleChannels(
            str(self.ui.cChannelPicker.currentText())[-1],
            str(self.ui.cChannelPickerRef.currentText())[-1]
        )

        sigSigBC = self.scope.integrateData(Sig, self.lrSig.getRegion())
        sigBgBC = self.scope.integrateData(Sig, self.lrBg.getRegion())
        refSigBC = self.scope.integrateData(Ref, self.lrSig.getRegion())
        refBgBC = self.scope.integrateData(Ref, self.lrBg.getRegion())

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








































