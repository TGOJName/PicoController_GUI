"""By the editor Oliver Tu: This program is modified from the Python Driver contributed by Ben Hammel (https://github.com/bdhammel/python_newport_controller)
to allow the picomotor to be controlled by a joystick/gamepad in Windows enviornment. TO RUN THE CODE, Python3 is required with 'PyUSB' and
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


    def __init__(self, idProduct, idVendor):
        """Initialize the Picomotor class with the spec's of the attached device

        Call self._connect to set up communication with usb device and endpoints 
        
        Args:
            idProduct (hex): Product ID of picomotor controller
            idVendor (hex): Vendor ID of picomotor controller
        """
        self.idProduct = idProduct
        self.idVendor = idVendor
        self._connect()

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
            raise ValueError('Device not found')

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
        print("Connected to Motor Controller Model {}. Firmware {} {} {}\n".format(
                                                    *resp.split(' ')
                                                    ))
        for m in range(1,5):
            resp = self.command("{}QM?".format(m))
            print("Motor #{motor_number}: {status}".format(
                                                    motor_number=m,
                                                    status=MOTOR_TYPE[resp[-1]]
                                                    ))



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


if __name__ == '__main__':
    from inputs import get_gamepad

    print('\n\n')
    print('#'*80)
    print('#\tPython controller for NewFocus Picomotor Controller')
    print('#'*80)
    print('\n')

    idProduct = None # '0x4000'
    idVendor = None  # '0x104d'

    if not (idProduct or idVendor):
        print('For Mac, run the following command in a new terminal window:')
        print('\t$ system_profiler SPUSBDataType\n')
        print('For Windows, check the "hardware id" in device manager:\n')
        print('Enter Product ID (default: 4000):')
        idProduct = input('> ') 
        if not bool(idProduct): # default pid and vid that works in my tests
            idProduct = '4000'
        print('Enter Vendor ID (default: 104D):')
        idVendor = input('> ') 
        if not bool(idVendor):
            idVendor = '104D'
        print('\n')

    # convert hex value in string to hex value
    idProduct = int(idProduct, 16)
    idVendor = int(idVendor, 16)

    # Initialize controller and start console
    controller = Controller(idProduct=idProduct, idVendor=idVendor)
    controller.command('ST')
    x_mkr = 0 # These makers are used to avoid the disfunction of motor caused by contradicting motions directions
    y_mkr = 0
    rx_mkr = 0
    ry_mkr = 0
    while True: #loop to detect the changes of joystick/gamepad
        events = get_gamepad()
        for event in events:
            if event.ev_type == 'Absolute':
                axis = event.state / 32768 # 32768 is the bound of the axis of the joystick we used, it is used to normalize the value of axis
                if event.code == 'ABS_X' and not rx_mkr:
                    #print(axis)
                    if -0.05 < axis and 0.05 > axis:
                        controller.command('1ST')
                        x_mkr = 0 
                    else:
                        controller.command('1VA'+str(int(2000 * abs(axis)))) # 2000 is the maximal speed for New Focus motor 8821-L
                        #if float(controller.command('1MV?')[-1]) * axis < 0: # Used to prevent fast change of motion direction, but seems uncessary
                        #    controller.command('1ST')
                        print(controller.command('MD?'))
                        if int(controller.command('1MD?')[-1]) == 1:
                            if axis > 0:
                                dir = '+'
                            else:
                                dir = '-'
                            x_mkr = 1
                            controller.command('1MV'+dir)
                elif event.code == 'ABS_Y' and not ry_mkr: # Same as the 'ABS_X' part but for an additional axis
                    #print(axis)
                    if -0.05 < axis and 0.05 > axis:
                        controller.command('2ST')
                        y_mkr = 0 
                    else:
                        controller.command('2VA'+str(int(2000 * abs(axis))))
                        #if float(controller.command('2MV?')[-1]) * axis < 0:
                        #    controller.command('2ST')
                        if int(controller.command('2MD?')[-1]) == 1:
                            if axis > 0:
                                dir = '+'
                            else:
                                dir = '-'
                            y_mkr = 1
                            controller.command('2MV'+dir)
                elif event.code == 'ABS_RX' and not x_mkr: # Same as the 'ABS_X' part but for an additional axis
                    #print(axis)
                    if -0.05 < axis and 0.05 > axis:
                        controller.command('1ST')
                        rx_mkr = 0 
                    else:
                        controller.command('1VA'+str(int(200 * abs(axis))))
                        #if float(controller.command('1MV?')[-1]) * axis < 0:
                        #    controller.command('1ST')
                        if int(controller.command('1MD?')[-1]) == 1:
                            if axis > 0:
                                dir = '+'
                            else:
                                dir = '-'
                            rx_mkr = 1
                            controller.command('1MV'+dir)
                elif event.code == 'ABS_RY' and not y_mkr: # Same as the 'ABS_X' part but for an additional axis
                    #print(axis)
                    if -0.05 < axis and 0.05 > axis:
                        controller.command('2ST')
                        ry_mkr = 0 
                    else:
                        controller.command('2VA'+str(int(200 * abs(axis))))
                        #if float(controller.command('2MV?')[-1]) * axis < 0:
                        #    controller.command('2ST')
                        if int(controller.command('2MD?')[-1]) == 1:
                            if axis > 0:
                                dir = '+'
                            else:
                                dir = '-'
                            ry_mkr = 1
                            controller.command('2MV'+dir)

