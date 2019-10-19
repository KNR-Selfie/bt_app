#!/usr/bin/env python

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys
import signal
import bluetooth as bt
from struct import pack, unpack
from qdarkstyle import load_stylesheet_pyqt
import select
from lxml import etree
from Queue import Queue
from binascii import unhexlify, hexlify


class SelfieApplication(QApplication):

    def __init__(self):
        super(SelfieApplication,self).__init__(['selfieApp'])
        self.parser = self.Parser()
        self.setWindowIcon(QIcon('logo.png'))
        self.lightStyle = self.styleSheet()
        self.darkStyle = load_stylesheet_pyqt()
        self.gui = self.Gui()
        self.parser.parseSignal.connect(self.gui.createCentralWidget)
        self.gui.changeModeSignal.connect(self.changeStyleSheet)
        self.connection = self.Connection()
        self.gui.connectButton.clicked.connect(self.connection.startConnecting)
        self.gui.disconnectButton.clicked.connect(self.connection.startDisconnecting)
        self.connection.connected.connect(self.gui.statusBar.setConnected)
        self.connection.disconnected.connect(self.gui.statusBar.setDisconnected)
        self.connection.connectionFailure.connect(self.Gui.WarningBox)
        self.connection.connected.connect(self.connection.startCommunication)
        self.gui.valueChanged.connect(self.connection.transmitSlot)
        self.gui.types.connect(self.connection.getTypes)
        self.parser.prse()
        self.connection.messageReceived.connect(self.gui.sensorSlot)
        self.gui.emptyTrigger.connect(self.connection.emptyTransmitSlot)
        sys.exit(self.exec_())


    class Gui(QMainWindow):
        mockSignal = pyqtSignal(etree._Element)
        changeModeSignal = pyqtSignal(bool)
        valueChanged = pyqtSignal(str,float)
        types = pyqtSignal(dict)
        emptyTrigger = pyqtSignal(str)
        def __init__(self):
            super(SelfieApplication.Gui,self).__init__()
            self.mockSignal.emit(etree.parse('settings.xml').getroot())
            self.setWindowTitle('selfieApp')
            self.showMaximized()
            signal.signal(signal.SIGINT,signal.SIG_DFL)

            #toolbar
            self.toolBar = QToolBar()
            self.toolBar.setMovable(False)
            self.connectButton = QPushButton('connect')
            self.disconnectButton = QPushButton('disconnect')
            self.changeModeButton = QPushButton('change to dark mode')
            self.changeModeButton.clicked.connect(self.changeChangeModeButton)
            self.toolBar.addWidget(self.connectButton)
            self.toolBar.addWidget(self.disconnectButton)
            self.toolBar.addWidget(self.changeModeButton)
            self.addToolBar(self.toolBar)
            self.codeFromSource = {}
            self.textFieldFromCode = {}
            self.targetFromCode = {}
            self.labelFromCode = {}
            self.typeLengths = {}
            self.msgTypes = {}
            self.emptyCodeFromSource = {}
            self.sliders = {}



            #statusbar
            self.connectionLabel = QLabel()
            self.statusBar = self.CustomStatusBar(self.connectionLabel)
            self.setStatusBar(self.statusBar)


        def createCentralWidget(self,root):
            mainWindow = QTabWidget()
            if root.tag == 'app':
                for tab in root:
                    tabW = QWidget()
                    tabWLayout = QHBoxLayout()
                    for row in tab:
                        rowW = QGroupBox(row.get('name'))
                        rowWLayout = QVBoxLayout()
                        rowWLayout.setAlignment(Qt.AlignTop)
                        for panel in row:
                            groupW = QGroupBox()
                            groupWLayout = QVBoxLayout()
                            groupW.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,QSizePolicy.Minimum))
                            groupWLayout.setAlignment(Qt.AlignTop)
                            if panel.tag == 'dyn':
                                dynW = QWidget()
                                dynWLayout = QVBoxLayout()
                                dynWLayout.setAlignment(Qt.AlignTop)
                                for var in panel:
                                    varW = QWidget()
                                    varWLayout = QHBoxLayout()
                                    varWLayout.setAlignment(Qt.AlignLeft)
                                    varName = QLabel(var.get('name'))
                                    varButton = QPushButton('send')
                                    varSlider = QSlider(Qt.Horizontal)
                                    
                                    if var.get('max'): varSlider.setMaximum(float(var.get('max'))*100)
                                    if var.get('min'): varSlider.setMinimum(float(var.get('min'))*100)
                                    if var.get('min') and var.get('max'): varSlider.setTickInterval(float(var.get('max'))-float(var.get('min')))
                                    textField = QLineEdit()
                                    varWLayout.addWidget(varName)
                                    varWLayout.addWidget(varButton)
                                    varWLayout.addWidget(varSlider)
                                    varWLayout.addWidget(textField)
                                    varW.setLayout(varWLayout)

                                    dynWLayout.addWidget(varW)
                                    dynW.setLayout(dynWLayout)

                                    varSlider.valueChanged.connect(self.sliderSlot)

                                    cd = unhexlify(var.get('code'))
                                    self.codeFromSource[varButton] = cd
                                    self.targetFromCode[cd] = varName
                                    self.textFieldFromCode[cd] = textField
                                    self.sliders[varSlider] = cd
                                    self.msgTypes[cd] = var.get('type')
                                groupWLayout.addWidget(dynW)
                            elif panel.tag == 'sens':
                                varW = QWidget()
                                varWLayout = QHBoxLayout()

                                varWLayout.setAlignment(Qt.AlignLeft)
                                varName = panel.get('name')
                                varLabel = QLabel('xd')

                                nameLabel = QLabel(varName)
                                cd = unhexlify(panel.get('code'))
                                self.labelFromCode[cd] = varLabel
                                self.msgTypes[cd] = panel.get('type')
                                varLabel.setStyleSheet('font-weight: bold')
                                varWLayout.addWidget(nameLabel)
                                varWLayout.addWidget(varLabel)
                                varW.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
                                varW.setLayout(varWLayout)
                                groupWLayout.addWidget(varW)
                            elif panel.tag == 'srv':
                                srvW = QWidget()
                                srvWLayout = QHBoxLayout()
                                srvWLayout.setAlignment(Qt.AlignLeft)
                                srvName = QLabel(panel.get('name'))
                                cd = unhexlify(panel.get('code'))
                                srvButton = QPushButton('send')
                                self.emptyCodeFromSource[srvButton] = cd
                                srvWLayout.addWidget(srvName)
                                srvWLayout.addWidget(srvButton)
                                srvW.setLayout(srvWLayout)
                                groupWLayout.addWidget(srvW)

                            groupW.setLayout(groupWLayout)
                            groupW.setTitle(panel.get('name'))
                            rowWLayout.addWidget(groupW)

                        rowW.setLayout(rowWLayout)
                        tabWLayout.addWidget(rowW)
                    tabW.setLayout(tabWLayout)
                    mainWindow.addTab(tabW, tab.get('name'))

            self.setCentralWidget(mainWindow)
            self.types.emit(self.msgTypes)
            self.connectWidgets()

        def changeValueSlot(self):
            code = self.codeFromSource[self.sender()]
            value = float(self.textFieldFromCode[code].text())
            self.valueChanged.emit(code,value)

        def emptySlot(self):
            code = self.emptyCodeFromSource[self.sender()]
            self.emptyTrigger.emit(code)

        def sliderSlot(self,val):
            code = self.sliders[self.sender()]
            self.textFieldFromCode[code].setText(str(val/100.))
            self.valueChanged.emit(code,val/100.)
        def connectWidgets(self):
            for button in self.codeFromSource.keys():
                button.clicked.connect(self.changeValueSlot)
            for button in self.emptyCodeFromSource.keys():
                button.clicked.connect(self.emptySlot)

        def sensorSlot(self,codes,values):
            for code, value in zip(codes, values):
                self.labelFromCode[code].setText(str(value))


        class CustomStatusBar(QStatusBar):
            def __init__(self, label):
                super(SelfieApplication.Gui.CustomStatusBar, self).__init__()
                self.defaultColor = self.palette().color(QPalette.Window)
                self.actualColor = self.defaultColor
                self.connectionLabel = label
                self.addWidget(self.connectionLabel)

            def paintEvent(self, QPaintEvent):
                self.gradient = QRadialGradient(self.width() / 2, self.height() / 2, self.width() * 2. / 3.)
                self.defaultColor = self.palette().color(QPalette.Window)
                self.gradient.setColorAt(0.0, self.actualColor)
                self.gradient.setColorAt(1.0, self.defaultColor)
                self.box = QRect(0, 0, self.width(), self.height())
                self.brush = QBrush(self.gradient)
                paint = QPainter(self)
                paint.setBrush(self.brush)
                paint.setPen(Qt.NoPen)
                paint.drawRect(self.box)

            def setDisconnected(self):
                self.connectionLabel.setText("Disconnected")
                self.actualColor = Qt.red
                self.repaint()

            def setConnected(self, name):
                self.connectionLabel.setText("Connected to " + name)
                self.actualColor = Qt.green
                self.repaint()

            def setDefault(self):
                self.actualColor = self.defaultColor
                self.repaint()

        class WarningBox(QMessageBox):
            def __init__(self):
                super(SelfieApplication.Gui.WarningBox,self).__init__()
                self.setIcon(QMessageBox.Critical)
                self.setStandardButtons(QMessageBox.Ok)
                self.setText('Couldn\'t connect to selfie!')
                self.setModal(True)
                self.exec_()

        def changeChangeModeButton(self):
            if self.changeModeButton.text() == 'change to dark mode':
                self.changeModeButton.setText('change to light mode')
                self.changeModeSignal.emit(True)
            else:
                self.changeModeButton.setText('change to dark mode')
                self.changeModeSignal.emit(False)

    class Connection(QObject):
        connected = pyqtSignal(QString)
        disconnected = pyqtSignal()
        connectionFailure = pyqtSignal()
        messageReceived = pyqtSignal(list,list)
        def __init__(self):
            super(SelfieApplication.Connection,self).__init__()
            self.selfieAddress = self.getSelfieAddress()
            self.communicationPort = 1
            self.connectionActive = False
            self.socket = bt.BluetoothSocket(bt.RFCOMM)
            self.connectThread = QThread()
            self.connectThread.run = self.connectToSelfie
            self.disconnectThread = QThread()
            self.disconnectThread.run = self.disconnectFromSelfie
            self.communicationThread = QThread()
            self.communicationThread.run = self.communication
            self.stopReq = False
            self.typeLengths = {}
            self.msgTypes = {}
            self.createTypeLengths()

            self.transmitQueue = Queue()

        def transmitSlot(self, code, value):
            self.transmitQueue.put(str(code) + str(pack(self.msgTypes[str(code)],value)))

        def emptyTransmitSlot(self,code):
            self.transmitQueue.put(str(code))

        def connectToSelfie(self):
            if not self.connectionActive:
                try:
                    self.socket = bt.BluetoothSocket(bt.RFCOMM)
                    self.socket.connect((self.selfieAddress, self.getCommunicationPort()))
                    srvName = bt.lookup_name(self.selfieAddress)
                except bt.BluetoothError:
                    self.connectionFailure.emit()
                else:
                    self.connectionActive = True
                    self.connected.emit(srvName)
                    print srvName

        def disconnectFromSelfie(self):
            if self.connectionActive:
                try:
                    self.stopReq = True
                    self.socket.close()
                except bt.BluetoothError:
                    print 'couldn\'t disconnect'
                else:
                    self.connectionActive = False
                    self.disconnected.emit()

        def communication(self):
            i = 0
            while not self.stopReq:
                try:
                    readable, writable, _ = select.select([self.socket],[self.socket],[])
                except:
                    self.disconnectFromSelfie()
                if len(readable):
                    msg = self.socket.recv(1000)
                    codes, values = self.seperateMsgs(msg)

                    self.messageReceived.emit(codes, values)

                if len(writable) and not self.transmitQueue.empty():
                    print 'sending'
                    msg = self.createMessage()
                    print repr(msg)
                    self.socket.send(msg)
            self.stopReq = False

        def createMessage(self):
            s = ''
            while not self.transmitQueue.empty():
                s+=self.transmitQueue.get()
            return s

        def seperateMsgs(self,msgs):
            i = 0
            sepCodes = []
            sepVals = []
            while i<len(msgs):
                code = msgs[i:i+3]
                i+=3
                value = None
                type = self.msgTypes[code]
                length = self.typeLengths[type]
                if length:
                    value = unpack(self.msgTypes[code],msgs[i:i+length])[0]
                    i+=length
                sepCodes.append(code)
                sepVals.append(value)
            ret = (sepCodes, sepVals)
            return ret

        def startConnecting(self):
            self.connectThread.start()

        def startDisconnecting(self):
            self.disconnectThread.start()

        def startCommunication(self):
            self.communicationThread.start()

        def getSelfieAddress(self):
            selfieAddress = ''
            with open('selfieMAC.txt','r') as file:
                selfieAddress = file.read()
            return selfieAddress

        def getCommunicationPort(self):
            return self.communicationPort

        def createTypeLengths(self):
            self.typeLengths['f'] = 4
            self.typeLengths['?'] = 1
            self.typeLengths['e'] = 0

        def getTypes(self,types):
            self.msgTypes = types

    class Parser(QObject):
        parseSignal = pyqtSignal(etree._Element)
        def prse(self):
            self.parseSignal.emit(etree.parse('settings.xml').getroot())


    def changeStyleSheet(self, mode):
        if mode:
            self.setStyleSheet(self.darkStyle)
        else:
            self.setStyleSheet(self.lightStyle)



if __name__ == '__main__':
    app = SelfieApplication()
