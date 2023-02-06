"""By the editor Oliver Tu: This program is modified from the Python Driver contributed by Ben Hammel (https://github.com/bdhammel/python_newport_controller)
to allow the picomotor to be controlled by a joystick/gamepad in Windows enviornment. TO RUN THE CODE, Python3 is required with 'PyUSB', 'PyQt5', and
'inputs' packages included. Besides, you also need to install the driver of the NewPort product from its official source.
The original annotation is shown below."""



"""Python Driver for NewFocus controllers

    __author__ = "Ben Hammel"
    __email__ = "bdhammel@gmail.com"
    __status__ = "Development"

Requirements:
    python (version > 2.7)
    re
    pyusb: $ pip install pyusb

    libusb-compat (USB backend): $ brew install libusb-compat

References:
    [1] pyusb tutorial, https://github.com/walac/pyusb/blob/master/docs/tutorial.rst
        5/13/2015
    [2] user manual, http://assets.newport.com/webDocuments-EN/images/8742_User_Manual_revB.pdf
        5/13/2015

Further Information:
    
Notes:
    1) Only tested with 1 8742 Model Open Loop Picomotor Controller.
    2) Current code will not support multiple controllers

TODO:
    1) Add in multi controller functionality
    2) Block illegal commands, not just commands with an invalid format
    3) Develop GUI
    4) Add in connection check.
        Execute the following commands ever .5 s
            1>1 MD?\r
            1>1 TP?\r
            1>2 TP?\r
            1>3 TP?\r
            1>4 TP?\r
            1>ERRSTR?\r
        Use http://stackoverflow.com/questions/6357850/how-do-i-run-some-python-code-in-another-process
"""

import usb.core
import usb.util
import re

NEWFOCUS_COMMAND_REGEX = re.compile("([0-9]{0,1})([a-zA-Z?]{2,})([0-9+-]*)")
MOTOR_TYPE = {
        "0":"No motor connected",
        "1":"Motor Unknown",
        "2":"'Tiny' Motor",
        "3":"'Standard' Motor"
        }

class Controller(object):
    """Picomotor Controller

    Example:

        >>> controller = Controller(idProduct=0x4000, idVendor=0x104d)
        >>> controller.command('VE?')
        
        >>> controller.start_console()
    """


    def __init__(self, idProduct, idVendor,lx,ly,rx,ry,fx,fy):

        # convert hex value in string to hex value
        idProduct = int(idProduct, 16)
        idVendor = int(idVendor, 16)


        self.idProduct = idProduct
        self.idVendor = idVendor
        self.connect_success = 0
        if self._connect(): # In the case of unsuccessful connection
            return None
        self.command('ST')
        self.marker = {'1':0, '2':0, '3':0, '4':0} # These makers are used to avoid multiple commmands on the same motor to cause disfunction
        self.lx = lx
        self.ly = ly
        self.rx = rx
        self.ry = ry
        self.fx = fx
        self.fy = fy
        self.position = 0
        

    def _connect(self):
        """Connect class to USB device 

        Find device from Vendor ID and Product ID
        Setup taken from [1]

        Raises:
            ValueError: if the device cannot be found by the Vendor ID and Product
                ID
            Assert False: if the input and outgoing endpoints can't be established
        """
        # find the device
        self.dev = usb.core.find(
                        idProduct=self.idProduct,
                        idVendor=self.idVendor
                        )
       
        if self.dev is None:
            return 1

        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        self.dev.set_configuration()

        # get an endpoint instance
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0,0)]

        self.ep_out = usb.util.find_descriptor(
            intf,
            # match the first OUT endpoint
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_OUT)

        self.ep_in = usb.util.find_descriptor(
            intf,
            # match the first IN endpoint
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_IN)

        assert (self.ep_out and self.ep_in) is not None
        
        # Confirm connection to user
        self.command('MC')
        resp = self.command('VE?')
        self.status = ''
        for m in range(1,5):
            resp = self.command("{}QM?".format(m))
            self.status += "Motor {motor_number}: {status}\n".format(
                                                    motor_number=m,
                                                    status=MOTOR_TYPE[resp[-1]]
                                                    )
        self.status = self.status[:-1]
        self.connect_success = 1

    def send_command(self, usb_command, get_reply=False):
        """Send command to USB device endpoint
        
        Args:
            usb_command (str): Correctly formated command for USB driver
            get_reply (bool): query the IN endpoint after sending command, to 
                get controller's reply

        Returns:
            Character representation of returned hex values if a reply is 
                requested
        """
        self.ep_out.write(usb_command)
        if get_reply:
            return self.ep_in.read(100)
            

    def parse_command(self, newfocus_command):
        """Convert a NewFocus style command into a USB command

        Args:
            newfocus_command (str): of the form xxAAnn
                > The general format of a command is a two character mnemonic (AA). 
                Both upper and lower case are accepted. Depending on the command, 
                it could also have optional or required preceding (xx) and/or 
                following (nn) parameters.
                cite [2 - 6.1.2]
        """
        m = NEWFOCUS_COMMAND_REGEX.match(newfocus_command)

        # Check to see if a regex match was found in the user submitted command
        if m:

            # Extract matched components of the command
            driver_number, command, parameter = m.groups()


            usb_command = command

            # Construct USB safe command
            if driver_number:
                usb_command = '1>{driver_number} {command}'.format(
                                                    driver_number=driver_number,
                                                    command=usb_command
                                                    )
            if parameter:
                usb_command = '{command} {parameter}'.format(
                                                    command=usb_command,
                                                    parameter=parameter
                                                    )

            usb_command += '\r'

            return usb_command
        else:
            print("ERROR! Command {} was not a valid format".format(
                                                            newfocus_command
                                                            ))


    def parse_reply(self, reply):
        """Take controller's reply and make human readable

        Args:
            reply (list): list of bytes returns from controller in hex format

        Returns:
            reply (str): Cleaned string of controller reply
        """

        # convert hex to characters 
        reply = ''.join([chr(x) for x in reply])
        return reply.rstrip()


    def command(self, newfocus_command):
        """Send NewFocus formated command

        Args:
            newfocus_command (str): Legal command listed in usermanual [2 - 6.2] 

        Returns:
            reply (str): Human readable reply from controller
        """
        usb_command = self.parse_command(newfocus_command)

        # if there is a '?' in the command, the user expects a response from
        # the driver
        if '?' in newfocus_command:
            get_reply = True
        else:
            get_reply = False

        reply = self.send_command(usb_command, get_reply)

        # if a reply is expected, parse it
        if get_reply:
            return self.parse_reply(reply)

    def loop(self):
        while True: #loop to detect the changes of joystick/gamepad
            events = get_gamepad()
            for event in events:
                #print(event.state)
                #print(self.marker)
                if event.ev_type == 'Absolute':
                    ex.joystick.setText('Joystick position\n'+str(event.state))
                    axis = event.state / joystick_range # 32768 is the bound of the axis of the joystick we used, it is used to normalize the value of axis
                    if event.code == 'ABS_X':
                        #print(axis)
                        if -0.01 < axis and 0.01 > axis:
                            self.command(self.lx+'ST')
                            self.marker[self.lx] = 0 
                        else:
                            self.command(self.lx+'VA'+str(int(2000 * abs(axis)))) # 2000 is the maximal speed for New Focus motor 8821-L
                            #if float(self.command('1MV?')[-1]) * axis < 0: # Used to prevent fast change of motion direction, but seems uncessary
                            #    self.command('1ST')
                            #print(self.command('MD?'))
                            if int(self.command(self.lx+'MD?')[-1]) == 1 and not self.marker[self.lx]:
                                if axis > 0:
                                    dir = '+'
                                else:
                                    dir = '-'
                                self.marker[self.lx] = 1
                                self.command(self.lx+'MV'+dir)
                    elif event.code == 'ABS_Y': # Same as the 'ABS_X' part but for an additional axis
                        #print(axis)
                        if -0.01 < axis and 0.01 > axis:
                            self.command(self.ly+'ST')
                            self.marker[self.ly] = 0 
                        else:
                            self.command(self.ly+'VA'+str(int(2000 * abs(axis))))
                            #if float(self.command('2MV?')[-1]) * axis < 0:
                            #    self.command('2ST')
                            if int(self.command(self.ly+'MD?')[-1]) == 1 and not self.marker[self.ly]:
                                if axis > 0:
                                    dir = '+'
                                else:
                                    dir = '-'
                                self.marker[self.ly] = 1
                                self.command(self.ly+'MV'+dir)
                    elif event.code == 'ABS_RX': # Same as the 'ABS_X' part but for an additional axis
                        #print(axis)
                        if -0.01 < axis and 0.01 > axis:
                            self.command(self.rx+'ST')
                            self.marker[self.rx] = 0 
                        else:
                            if self.fx:
                                f1 = 0.1
                            else:
                                f1 = 1
                            self.command(self.rx+'VA'+str(int(2000 * abs(axis) * f1)))
                            #if float(self.command('1MV?')[-1]) * axis < 0:
                            #    self.command('1ST')
                            if int(self.command(self.rx+'MD?')[-1]) == 1 and not self.marker[self.rx]:
                                if axis > 0:
                                    dir = '+'
                                else:
                                    dir = '-'
                                self.marker[self.rx] = 1
                                self.command(self.rx+'MV'+dir)
                    elif event.code == 'ABS_RY': # Same as the 'ABS_X' part but for an additional axis
                        #print(axis)
                        if -0.01 < axis and 0.01 > axis:
                            self.command(self.ry+'ST')
                            self.marker[self.ry] = 0 
                        else:
                            if self.fy:
                                f2 = 0.1
                            else:
                                f2 = 1                            
                            self.command(self.ry+'VA'+str(int(2000 * abs(axis) * f2)))
                            #if float(self.command('2MV?')[-1]) * axis < 0:
                            #    self.command('2ST')
                            if int(self.command(self.ry+'MD?')[-1]) == 1 and not self.marker[self.ry]:
                                if axis > 0:
                                    dir = '+'
                                else:
                                    dir = '-'
                                self.marker[self.ry] = 1
                                self.command(self.ry+'MV'+dir)


#GUI
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QGridLayout, QComboBox, QLineEdit, QLabel, QCheckBox
from PyQt5.QtCore import  QThread

class Worker(QThread):
    def __init__(self, work):
        super(QThread, self).__init__()
        self.work = work

    def run(self):
        self.work()

class ui(QWidget):

    def __init__(self):
        super(ui,self).__init__()

        self.PIDTitle = QLabel('Product ID (PID, by default 4000): ')
        self.VIDTitle = QLabel('Vendor ID (VID, by default 104D): ')
        self.PIDEdit = QLineEdit(self)
        self.VIDEdit = QLineEdit(self)
        self.PIDEdit.setText('4000')
        self.VIDEdit.setText('104D')

        self.leftxTitle = QLabel('Left Stick X-axis')
        self.leftyTitle = QLabel('Left Stick Y-axis')
        self.rightxTitle = QLabel('Right Stick X-axis')
        self.rightyTitle = QLabel('Right Stick Y-axis')

        self.connector = QPushButton('Connect Motors', self)
        self.connector.clicked.connect(self.motorConnect)
        self.restarter = QPushButton('Restart', self)
        self.restarter.clicked.connect(self.restart)
        self.mstatus = QLabel('Motor 1: \nMotor 2: \nMotor 3: \nMotor 4: ')
        self.notice = QLabel('To get PID and VID:\nFor Mac, run the following command in a new terminal window: "$ system_profiler SPUSB'
            +'DataType"\nFor Windows, check Device Manager -> <device name> -> property -> details -> hardware id')
        self.joystick = QLabel('')

        self.leftxMode = QComboBox(self)
        self.leftxMode.addItem('Motor 1')
        self.leftxMode.addItem('Motor 2')
        self.leftxMode.addItem('Motor 3')
        self.leftxMode.addItem('Motor 4')
        self.leftxMode.activated.connect(self.leftxActivated)
        self.leftyMode = QComboBox(self)
        self.leftyMode.addItem('Motor 1')
        self.leftyMode.addItem('Motor 2')
        self.leftyMode.addItem('Motor 3')
        self.leftyMode.addItem('Motor 4')
        self.leftyMode.activated.connect(self.leftyActivated)
        self.rightxMode = QComboBox(self)
        self.rightxMode.addItem('Motor 1')
        self.rightxMode.addItem('Motor 2')
        self.rightxMode.addItem('Motor 3')
        self.rightxMode.addItem('Motor 4')
        self.rightxMode.activated.connect(self.rightxActivated)
        self.rightyMode = QComboBox(self)
        self.rightyMode.addItem('Motor 1')
        self.rightyMode.addItem('Motor 2')
        self.rightyMode.addItem('Motor 3')
        self.rightyMode.addItem('Motor 4')
        self.rightyMode.activated.connect(self.rightyActivated)

        self.finex = QCheckBox(self)
        self.finex.setText('Fine Tuning')
        self.finex.setChecked(True)
        self.finex.stateChanged.connect(self.fxsig)
        self.finey = QCheckBox(self)
        self.finey.setText('Fine Tuning')
        self.finey.setChecked(True)
        self.finey.stateChanged.connect(self.fysig)

        self.leftxMode.setEnabled(False)
        self.leftyMode.setEnabled(False)
        self.rightxMode.setEnabled(False)
        self.rightyMode.setEnabled(False)
        self.finex.setEnabled(False)
        self.finey.setEnabled(False)

        #Alignment
        self.grid = QGridLayout(self)
        self.grid.setSpacing(10)
 
        self.grid.addWidget(self.PIDTitle, 0, 0)
        self.grid.addWidget(self.PIDEdit, 0, 1)
        self.grid.addWidget(self.VIDTitle, 1, 0)
        self.grid.addWidget(self.VIDEdit, 1, 1)
        self.grid.addWidget(self.connector, 0, 2)
        self.grid.addWidget(self.restarter, 1, 2)
        self.grid.addWidget(self.mstatus, 0, 3,2,2)
        self.grid.addWidget(self.leftxTitle, 2, 0)
        self.grid.addWidget(self.rightxTitle, 2, 2)
        self.grid.addWidget(self.leftxMode, 2, 1)
        self.grid.addWidget(self.rightxMode, 2, 3)
        self.grid.addWidget(self.finex, 2, 4)
        self.grid.addWidget(self.leftyTitle, 3, 0)
        self.grid.addWidget(self.rightyTitle, 3, 2)
        self.grid.addWidget(self.leftyMode, 3, 1)
        self.grid.addWidget(self.rightyMode, 3, 3)
        self.grid.addWidget(self.finey, 3, 4)
        self.grid.addWidget(self.notice, 4, 0,1,4)
        self.grid.addWidget(self.joystick, 4, 4)
        
        self.setLayout(self.grid) 
        self.leftxMode.setCurrentIndex(0)
        self.rightxMode.setCurrentIndex(0)
        self.leftyMode.setCurrentIndex(1)
        self.rightyMode.setCurrentIndex(1)
        self.setGeometry(300, 300, 350, 300)
        self.setWindowTitle('Controller Setting')    
        self.show()
        
    def leftxActivated(self):  #Functions of selection bar on potential type
        self.controller.lx = str(self.leftxMode.currentIndex()+1)

    def rightxActivated(self):  #Functions of selection bar on potential type
        self.controller.rx = str(self.rightxMode.currentIndex()+1)

    def leftyActivated(self):  #Functions of selection bar on potential type
        self.controller.ly = str(self.leftyMode.currentIndex()+1)

    def rightyActivated(self):  #Functions of selection bar on potential type
        self.controller.ry = str(self.rightyMode.currentIndex()+1)
    
    def fxsig(self):
        self.controller.fx = self.finex.isChecked()
    
    def fysig(self):
        self.controller.fy = self.finey.isChecked()
    
    def motorConnect(self):
        self.controller = Controller(self.PIDEdit.text(), self.VIDEdit.text(),str(self.leftxMode.currentIndex()+1),
            str(self.leftyMode.currentIndex()+1),str(self.rightxMode.currentIndex()+1),str(self.rightyMode.currentIndex()+1),self.finex.isChecked(),self.finey.isChecked())
        if self.controller.connect_success:
            self.mstatus.setText(self.controller.status)
            self.looper = Worker(self.controller.loop)
            self.looper.start()
            self.connector.setEnabled(False)
            self.notice.setText('')
            self.leftxMode.setEnabled(True)
            self.leftyMode.setEnabled(True)
            self.rightxMode.setEnabled(True)
            self.rightyMode.setEnabled(True)
            self.finex.setEnabled(True)
            self.finey.setEnabled(True)
            self.joystick.setText('Joystick Position\n')
        else:
            self.notice.setText('To get PID and VID:\nFor Mac, run the following command in a new terminal window: "$ system_profiler SPUSB'
                +'DataType"\nFor Windows, check Device Manager -> <device name> -> property -> details -> hardware id\nNo Device Detected!')
    
    def restart(self):
        os.execl(sys.executable, sys.executable, * sys.argv)


if __name__ == '__main__':
    from inputs import get_gamepad
    import os
    joystick_range = 32768
    app = QApplication(sys.argv)
    ex = ui()
    ex.show()
    sys.exit(app.exec_())
