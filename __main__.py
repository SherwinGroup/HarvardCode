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
import InstsAndQt.Instruments

InstsAndQt.Instruments.PRINT_OUTPUT = False
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class Win(QtGui.QMainWindow):
    leakSig = QtCore.pyqtSignal(object)
    oscSig = QtCore.pyqtSignal(object)
    statusSig = QtCore.pyqtSignal(object)
    intSig = QtCore.pyqtSignal(object)
    sigPyroData = QtCore.pyqtSignal(object)
    sigSignalData = QtCore.pyqtSignal(object)

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
        self.intValues = np.empty((0,3))
        self.scopeValues = None
        self.pyroData = None
        self.signalData = None
        self.pyroDataAve = None
        self.signalDataAve = None
        self.saveLoc = ''
        self.voltage = 0.0
        self.numVoltageSteps = 0

        self.settings = {}
        self.settings['collectScope'] = True
        self.settings['pauseScope'] = False

        self.openOsc()
        self.openKeith()

        self.thScopeCollection = threading.Thread(target = self.collectScopeLoop)
        self.thScopeCollection.start()
        
    def initUI(self):
        #Import ui file from designer
        self.ui=Ui_MainWindow()
        self.ui.setupUi(self)  
        
        #Define the plot widgets where data is updated
        self.leakGraph = self.ui.gLeakage.plot(pen='k')
        plotitem = self.ui.gLeakage.getPlotItem()
        plotitem.setTitle('Leakage Current')
        plotitem.setLabel('left',text='Current',units='A')
        plotitem.setLabel('bottom',text='voltage', units='V')


        self.ui.gOscilloscopePyro.plotItem.setTitle("Reference Signal")
        self.ui.gOscilloscopePyro.plotItem.setLabel('left', text='Voltage', units='V')
        self.ui.gOscilloscopePyro.plotItem.setLabel('bottom', text='Time', units='s')
        self.pyroPlot = self.ui.gOscilloscopePyro.plot(pen='k')


        self.ui.gOscilloscopeWave.plotItem.setTitle("Waveform Signal")
        self.ui.gOscilloscopeWave.plotItem.setLabel('left', text='Voltage', units='V')
        self.ui.gOscilloscopeWave.plotItem.setLabel('bottom', text='Time', units='s')
        self.signalPlot = self.ui.gOscilloscopeWave.plot(pen='k')


        # initialize integration regions
        bgCol = pg.mkBrush(QtGui.QColor(255, 0, 0, 50))
        sgCol = pg.mkBrush(QtGui.QColor(0, 255, 0, 50))
        self.boxcars = [None] * 4

        self.boxcars[0] = pg.LinearRegionItem([0, 0], brush=bgCol)
        self.boxcars[1] = pg.LinearRegionItem([0, 0], brush=sgCol)
        self.boxcars[2] = pg.LinearRegionItem([0, 0], brush=bgCol)
        self.boxcars[3] = pg.LinearRegionItem([0, 0], brush=sgCol)

        # connect them to something to change the values of the textboxes
        for b in self.boxcars:
            b.sigRegionChangeFinished.connect(self.updateLinearRegionValues)

        self.ui.gOscilloscopePyro.addItem(self.boxcars[0])
        self.ui.gOscilloscopePyro.addItem(self.boxcars[1])
        self.ui.gOscilloscopeWave.addItem(self.boxcars[2])
        self.ui.gOscilloscopeWave.addItem(self.boxcars[3])

        self.ui.bOscPause.clicked.connect(self.togglePause)
        self.ui.bScanPause.clicked.connect(self.togglePause)

        # Make an iterable list for the linear region text boxes and connect
        # them to something to handle the updates
        lrtb = [None]*4
        lrtb[0] = [self.ui.tPyroBGSt, self.ui.tPyroBGEn]
        lrtb[1] = [self.ui.tPyroSGSt, self.ui.tPyroSGEn]
        lrtb[2] = [self.ui.tWaveBGSt, self.ui.tWaveBGEn]
        lrtb[3] = [self.ui.tWaveSGSt, self.ui.tWaveSGEn]

        for i in lrtb:
            for j in i:
                j.setText('0.0')
                j.textAccepted.connect(self.updateLinearRegionsFromText)
        self.linearRegionTextBoxes = lrtb

        self.ui.bInitOsc.clicked.connect(self.initIntRegions)


        self.intGraph = self.ui.gValueVsV.plot(pen='k')
        plotitem = self.ui.gValueVsV.getPlotItem()
        plotitem.setTitle('Waveform')
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
        # self.ui.cChannelPicker.currentIndexChanged.connect(self.changeChannel)
        self.ui.bSaveDirectory.clicked.connect(self.updateSaveLoc)
        # self.ui.bResetLeak.clicked.connect(self.resetLeak)
        
#        self.ui.tIntEnd.editingFinished.connect(self.updateLR)
#        self.ui.tIntStart.editingFinished.connect(self.updateLR)

        self.ui.splitter_2.setStretchFactor(0, 50)
        self.ui.splitter_2.setStretchFactor(1, 1)
        self.ui.splitter_4.setStretchFactor(0, 50)
        self.ui.splitter_4.setStretchFactor(1, 1)

        self.show()
        
#    def updateLR(self):
#        self.integrationRegion.setBounds([float(self.ui.tIntStart.text()), float(self.ui.tIntEnd.text())])

    def updateLinearRegionValues(self):
        sender = self.sender()
        sendidx = -1
        for (i, v) in enumerate(self.boxcars):
            #I was debugging something. I tried to use id(), which is effectively the memory
            #location to try and fix it. Found out it was anohter issue, but
            #id() seems a little safer(?) than just equating them in the sense that
            #it's explicitly asking if they're the same object, isntead of potentially
            #calling some weird __eq__() pyqt/graph may have set up
            if id(sender) == id(v):
                sendidx = i
        i = sendidx
        #Just being paranoid, no reason to think it wouldn't find the proper thing
        if sendidx<0:
            return

        for ii, v in enumerate(self.linearRegionTextBoxes[i]):
            v.blockSignals(True)
            v.setText('{:.6g}'.format(sender.getRegion()[ii]*1e3))
            v.blockSignals(False)

        # self.linearRegionTextBoxes[i][0].setText('{:.6g}'.format(sender.getRegion()[0]))
        # self.linearRegionTextBoxes[i][1].setText('{:.6g}'.format(sender.getRegion()[1]))

    def updateLinearRegionsFromText(self):
        sender = self.sender()
        for i in self.linearRegionTextBoxes:
            for j in i:
                j.blockSignals(True)

        #figure out where this was sent
        sendi, sendj = -1, -1
        for (i, v)in enumerate(self.linearRegionTextBoxes):
            for (j, w) in enumerate(v):
                if id(w) == id(sender):
                    sendi = i
                    sendj = j

        i = sendi
        j = sendj
        # if i==4 and j==1:
        #     sender.setText(str(
        #         float(self.linearRegionTextBoxes[-1][0].text())+40e-9
        #     ))
        curVals = list(self.boxcars[i].getRegion())
        curVals[j] = float(sender.text())*1e-3
        print curVals
        self.boxcars[i].blockSignals(True)
        self.boxcars[i].setRegion(tuple(curVals))
        self.boxcars[i].blockSignals(False)
        for i in self.linearRegionTextBoxes:
            for j in i:
                j.blockSignals(False)

    def initIntRegions(self):
        if self.pyroData is None:
            return
        for i in self.linearRegionTextBoxes:
            for j in i:
                j.blockSignals(True)

        l = self.pyroData.shape[0]
        midValue = self.pyroData[l/2,0]
        for i in self.boxcars:
            i.setRegion((midValue, midValue))
        for i in self.linearRegionTextBoxes:
            for j in i:
                j.blockSignals(False)
        # for i in self.boxcars:
        #     i.blockSignals(True)




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
        self.settings['collectScope'] = False
        try:
            self.pausingLoop.exit()
        except:
            pass
        try:
            self.thScopeCollection.join()
        except:
            pass
        self.scope.close()
        self.keith.close()

        self.close()

    def togglePause(self, val):
        newVal = not val
        self.ui.bOscPause.setChecked(val)
        self.ui.bScanPause.setChecked(val)

    def collectScopeLoop(self):
        while self.settings['collectScope']:
            if self.ui.bOscPause.isChecked():
                self.scope.write(':RUN')

                self.pausingLoop = QtCore.QEventLoop()
                self.ui.bOscPause.clicked.connect(self.pausingLoop.exit)
                self.pausingLoop.exec_()
            pyroChannel = str(self.ui.cChannelPickerRef.currentText())[-1]
            signalChannel = str(self.ui.cChannelPicker.currentText())[-1]
            pyroData, signalData = self.scope.getMultipleChannels(pyroChannel, signalChannel)
            if not self.ui.bOscPause.isChecked():
                self.pyroData = pyroData
                self.signalData = signalData
                self.oscSig.emit([])


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
        
        #Start the thread to take the data
        self.numVoltageSteps = 0
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
        self.runFlag = False
        self.scope.breakLoop = True
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
            raise
            return

        self.saveLeakage()
        self.abortScan()

        
    def doMeasurementPoint(self, voltage, reverse = False):
        self.voltage = voltage
        if not self.numVoltageSteps%self.ui.tMeasureEvery.value()==0:
            self.numVoltageSteps += 1
            return
        self.numVoltageSteps += 1
        self.statusSig.emit('Measuring. Voltage: '+str(voltage))

        numValues = 0
        while numValues <= self.ui.tOAverages.value()-1:
            self.measuringWaitingLoop = QtCore.QEventLoop()
            self.oscSig.connect(self.measuringWaitingLoop.exit)
            self.measuringWaitingLoop.exec_()
            if numValues == 0:
                self.pyroDataAve = np.array(self.pyroData)
                self.signalDataAve = np.array(self.signalData)
            else:
                self.pyroDataAve[:,1] += self.pyroData[:,1]
                self.signalDataAve[:,1] += self.signalData[:,1]
            numValues += 1
            self.statusSig.emit('Measuring. Voltage: {}, num: {}'.format(voltage, numValues))

        self.pyroDataAve[:,1] /= numValues
        self.signalDataAve[:,1] /= numValues



        refBgBC = self.scope.integrateData(self.pyroDataAve, self.boxcars[0].getRegion())
        refSigBC = self.scope.integrateData(self.pyroDataAve, self.boxcars[1].getRegion())
        sigBgBC = self.scope.integrateData(self.signalDataAve, self.boxcars[2].getRegion())
        sigSigBC = self.scope.integrateData(self.signalDataAve, self.boxcars[3].getRegion())

        
        self.leakSig.emit([[voltage, self.keith.getValue()]])
        # indexes = (self.time>start)&(self.time<end)
#        indexes = np.array([0 for i in len(self.time) if (i>start and i<end) else 0])
#         self.intSig.emit([[voltage, sum(indexes*self.scopeValues)]])
        self.intSig.emit([[voltage, refSigBC-refBgBC, sigSigBC-sigBgBC]])

        if reverse:
            self.saveOsc(str(voltage)+'b')
        else:
            self.saveOsc(voltage)
        return True
            
    def updateLeakage(self, data):
        self.leakValues = np.append(self.leakValues, data, axis=0)
        self.leakGraph.setData(self.leakValues[:,0], self.leakValues[:,1])
    
    def updateOsc(self, data):
        # self.oscGraph.setData(self.time, self.scopeValues)
        self.pyroPlot.setData(self.pyroData)
        self.signalPlot.setData(self.signalData)

    def updateIntegration(self, data):
        self.intValues = np.append(self.intValues, data, axis=0)
        self.intGraph.setData(self.intValues[:,0], self.intValues[:,-1])
        
    def changeChannel(self, idx):
        self.oscChannel = 'CH'+str(idx+1)
        self.scope.Channel = self.oscChannel
        self.scope.CHA = self.oscChannel
        self.scope.setChannel(self.oscChannel)
        self.scope.getScopeValues()
    
    def saveOsc(self, v):
        baseName = str(self.ui.tSave.text())
        baseName += "referenceDetector"
        saveName = baseName + str(v)
        
        np.savetxt(self.saveLoc+saveName, self.pyroDataAve,
                   header = 'Time(s), Voltage(V)')


        baseName = str(self.ui.tSave.text())
        baseName += "signalWaveform"
        saveName = baseName + str(v)

        np.savetxt(self.saveLoc+saveName, self.signalDataAve,
                   header = 'Time(s), Voltage(V)')
        
    def saveLeakage(self):
        np.savetxt(self.saveLoc + str(self.ui.tSave.text())+'Leakage', self.leakValues, header='Voltage(V), Current(A)')
        header = 'pyro background boxcar: {}'.format(self.boxcars[0].getRegion())
        header += '\npyro signal boxcar: {}'.format(self.boxcars[1].getRegion())
        header += '\nGraphene background boxcar: {}'.format(self.boxcars[2].getRegion())
        header += '\nGraphene signal boxcar: {}'.format(self.boxcars[3].getRegion())
        header += '\nBGVoltage(V), Ave Ref Det (V), Ave Graphene response(V)'
        np.savetxt(self.saveLoc + str(self.ui.tSave.text())+'Integrated', self.intValues, header=header)
        
        
    def updateSaveLoc(self):
        fname = str(QtGui.QFileDialog.getExistingDirectory(self, "Choose File Directory...",directory=self.saveLoc))
        print 'fname',fname
        if fname == '':
            return
        self.saveLoc = fname + '/'
        
    def resetLeak(self):
        self.leakValues = np.empty((0,2))
        self.leakGraph.setData([],[])
        self.intValues = np.empty((0,3))
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








































