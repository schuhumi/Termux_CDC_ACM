import usb
import usb.core
import usb.util
import usb.control

CH340_bInterfaceClass = 0xff

def check_is_CH340(dev):
    return dev.idVendor==0x1A86 and dev.idProduct==0x7523

class serial_CH340():
    def __init__(self, dev, baudrate):
        self.dev = dev
        self.baudrate = baudrate
        self.cfg = self.dev.get_active_configuration()
        
        self.interface = usb.util.find_descriptor(self.cfg, bInterfaceClass=CH340_bInterfaceClass)
        usb.util.claim_interface(self.dev, self.interface)
        
        self.endpoint_OUT = None
        self.endpoint_IN = None
        for endpoint in self.interface.endpoints():
            if endpoint.bmAttributes==usb.ENDPOINT_TYPE_BULK: # Both endpoints have the "Bulk" attribute
                # What's IN and OUT can be distinguished by bit 7 of the Endpoint Address
                if endpoint.bEndpointAddress & 1<<7: # Bit7 of the bEndpointAddress determines the direction: 0=OUT, 1=IN
                    self.endpoint_IN = endpoint
                else:
                    self.endpoint_OUT = endpoint
        if self.endpoint_OUT == None:
            print("serial_CH340:: Error: Could not find OUT-Endpoint!")
        if self.endpoint_IN == None:
            print("serial_CH340:: Error: Could not find IN-Endpoint!")
        
        # OUT-Transfer, parameters are: bmRequestType, bmRequest, wValue, wIndex and data-payload
        # Helpful: https://gist.github.com/z4yx/8d9ecad151dad351fbbb
        self.dev.ctrl_transfer(
            usb.TYPE_VENDOR | usb.ENDPOINT_OUT,
            0xa1,
            0x00,
            self.interface.index, # interface index
            None)   # No data-payload
        self.dev.ctrl_transfer(
            usb.TYPE_VENDOR | usb.ENDPOINT_OUT,
            0x9a,
            0x2518,
            0x0050,
            None)   # No data-payload
        self.dev.ctrl_transfer(
            usb.TYPE_VENDOR | usb.ENDPOINT_OUT,
            0xa1,
            0x501f,
            0xd90a,
            None)   # No data-payload
            
        # set baud rate
        baud = {
            2400:   (0xd901, 0x0038), 
            4800:   (0x6402, 0x001f), 
            9600:   (0xb202, 0x0013), 
            19200:  (0xd902, 0x000d), 
            38400:  (0x6403, 0x000a), 
            115200: (0xcc03, 0x0008)
            }
        if not self.baudrate in baud:
            print(f"serial_CH340:: Error: requested {self.baudrate=} not in baud table!")
            
        self.dev.ctrl_transfer(
            usb.TYPE_VENDOR | usb.ENDPOINT_OUT,
            0x9a,
            0x1312,
            baud[self.baudrate][0],
            None)   # No data-payload
        self.dev.ctrl_transfer(
            usb.TYPE_VENDOR | usb.ENDPOINT_OUT,
            0x9a,
            0x0f2c,
            baud[self.baudrate][1],
            None)   # No data-payload
        
        
        
    def purge(self):
        # Purge whatever the printer has sent while not being connected
        while(True):
            try:
                self.endpoint_IN.read(64, timeout=1) # 1 millisecond timeout
            except usb.core.USBTimeoutError:
                break
        
    def write(self, data):
        self.endpoint_OUT.write(data)
        
    def read(self, size=1024, timeout=1):
        try:
            return self.endpoint_IN.read(size, timeout=timeout).tobytes()
        except usb.core.USBTimeoutError:
            return b''
        
        
    def close(self):
        usb.util.release_interface(self.dev, self.interface)
