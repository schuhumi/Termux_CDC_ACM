import usb
import usb.core
import usb.util
import usb.control

def check_is_CDCACM(dev):
    cfg = dev.get_active_configuration()
    interface_CDC_Comm = usb.util.find_descriptor(cfg, bInterfaceClass=usb.CLASS_COMM)
    interface_CDC_Data = usb.util.find_descriptor(cfg, bInterfaceClass=usb.CLASS_DATA)
    if (interface_CDC_Comm is None) or (interface_CDC_Data is None):
        return False
    else:
        return True

class serial_CDCACM():
    def __init__(self, dev, baudrate):
        self.dev = dev
        self.baudrate = baudrate
        self.cfg = self.dev.get_active_configuration()
        
        # CDC-Interfaces can be identified using their Interface Class
        self.interface_CDC_Comm = usb.util.find_descriptor(self.cfg, bInterfaceClass=usb.CLASS_COMM)
        self.interface_CDC_Data = usb.util.find_descriptor(self.cfg, bInterfaceClass=usb.CLASS_DATA)
        
        print(f"{self.interface_CDC_Comm=}")
        print(f"{self.interface_CDC_Data=}")
        
        # Lock usb device
        usb.util.claim_interface(self.dev, self.interface_CDC_Data)
        usb.util.claim_interface(self.dev, self.interface_CDC_Comm)
        
        # Now we need to find the endpoints where we can transmit and receive serial data
        # Helpful: https://www.keil.com/pack/doc/mw/USB/html/_u_s_b__endpoint__descriptor.html
        self.endpoint_OUT = None
        self.endpoint_IN = None
        for endpoint in self.interface_CDC_Data.endpoints():
            if endpoint.bmAttributes==usb.ENDPOINT_TYPE_BULK: # Both endpoints have the "Bulk" attribute
                # What's IN and OUT can be distinguished by bit 7 of the Endpoint Address
                if endpoint.bEndpointAddress & 1<<7: # Bit7 of the bEndpointAddress determines the direction: 0=OUT, 1=IN
                    self.endpoint_IN = endpoint
                else:
                    self.endpoint_OUT = endpoint
        if self.endpoint_OUT == None:
            print("serial_CDCACM:: Error: Could not find OUT-Endpoint!")
        if self.endpoint_IN == None:
            print("serial_CDCACM:: Error: Could not find IN-Endpoint!")
                
        
        # Configure as baudrate (<- in little endian) and 8N1
        serialConf = bytearray(list((self.baudrate).to_bytes(length=6, byteorder="little")) + [0x08])
        
        # OUT-Transfer, parameters are: bmRequestType, bmRequest, wValue, wIndex and data-payload
        # Helpful: https://github.com/NordicPlayground/node-usb-cdc-acm/blob/master/src/usb-cdc-acm.js
        self.dev.ctrl_transfer( # set line state
            usb.ENDPOINT_OUT | usb.TYPE_CLASS | usb.RECIP_INTERFACE,   # bmRequestType: [host-to-device, type: class, recipient: iface]
            0x22,   # SET_CONTROL_LINE_STATE
            0x00, #0x02 | 0x01, # 0x02 "Activate carrier" & 0x01 "DTE is present" 
            self.interface_CDC_Comm.index, # interface index
            None)   # No data-payload
        self.dev.ctrl_transfer( # set line coding
            usb.ENDPOINT_OUT | usb.TYPE_CLASS | usb.RECIP_INTERFACE,   # bmRequestType: [host-to-device, type: class, recipient: iface]
            0x20,   # SET_LINE_CODING
            0,      # Always zero
            self.interface_CDC_Comm.index, # interface index
            serialConf) # data-payload
    
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
        usb.util.release_interface(self.dev, self.interface_CDC_Data)
        usb.util.release_interface(self.dev, self.interface_CDC_Comm)
