#!/usr/bin/env python3

import usb
import usb.core
import usb.util
import usb.control
from usblib import device_from_fd
import sys
import array
import os
import time
from multiprocessing.connection import Client
from multiprocessing.connection import Listener

def main(fd, debug=False):
    dev = device_from_fd(fd)
    
    if dev.is_kernel_driver_active(0):
        dev.detach_kernel_driver(0)
        print("kernel driver detached")
    else:
        print("no kernel driver attached")
    
    # Get endpoint
    cfg = dev.get_active_configuration()
    print(cfg)
    
    # CDC-Interfaces can be identified using their Interface Class
    interface_CDC_Comm = usb.util.find_descriptor(cfg, bInterfaceClass=usb.CLASS_COMM)
    interface_CDC_Data = usb.util.find_descriptor(cfg, bInterfaceClass=usb.CLASS_DATA)
    
    # Lock usb device
    usb.util.claim_interface(dev, interface_CDC_Data)
    usb.util.claim_interface(dev, interface_CDC_Comm)
    
    # Now we need to find the endpoints where we can transmit and receive serial data
    # Helpful: https://www.keil.com/pack/doc/mw/USB/html/_u_s_b__endpoint__descriptor.html
    endpoint_OUT = None
    endpoint_IN = None
    for endpoint in interface_CDC_Data.endpoints():
        if endpoint.bmAttributes==usb.ENDPOINT_TYPE_BULK: # Both endpoints have the "Bulk" attribute
            # What's IN and OUT can be distinguished by bit 7 of the Endpoint Address
            if endpoint.bEndpointAddress & 1<<7: # Bit7 of the bEndpointAddress determines the direction: 0=OUT, 1=IN
                endpoint_IN = endpoint
            else:
                endpoint_OUT = endpoint
    if endpoint_OUT == None:
        print("cdcDaemon:: Error: Could not find OUT-Endpoint!")
    if endpoint_IN == None:
        print("cdcDaemon:: Error: Could not find IN-Endpoint!")
    
    # Configure usb-serial-converter
    baudrate = int(os.environ["TERMUX_CDC_ACM_BAUDRATE"]) # From environment variable
    # Configure as baudrate (<- in little endian) and 8N1
    serialConf = bytearray(list((baudrate).to_bytes(length=6, byteorder="little")) + [0x08])
    
    # OUT-Transfer, parameters are: bmRequestType, bmRequest, wValue, wIndex and data-payload
    # Helpful: https://github.com/NordicPlayground/node-usb-cdc-acm/blob/master/src/usb-cdc-acm.js
    dev.ctrl_transfer( # set line state
        0x21,   # bmRequestType: [host-to-device, type: class, recipient: iface]
        0x22,   # SET_CONTROL_LINE_STATE
        0x00, #0x02 | 0x01, # 0x02 "Activate carrier" & 0x01 "DTE is present" 
        interface_CDC_Comm.index, # interface index
        None)   # No data-payload
    dev.ctrl_transfer( # set line coding
        0x21,   # bmRequestType: [host-to-device, type: class, recipient: iface]
        0x20,   # SET_LINE_CODING
        0,      # Always zero
        interface_CDC_Comm.index, # interface index
        serialConf) # data-payload
    
    # Create Ocotoprint-In-Printer-Out-listener for octoprint to attach to
    OIPOaddress = ('localhost', 6001)     # family is deduced to be 'AF_INET'
    OIPOlistener = Listener(OIPOaddress, authkey=b'secret password')
    
    # Connect to Octoprint-Out-Printer-In-listener of octoprint
    OOPIaddress = ('localhost', 6000)
    OOPIconn = Client(OOPIaddress, authkey=b'secret password')
    
    # Accept connection of octoprint on OIPOlistener
    OIPOconn = OIPOlistener.accept()
    
    # Purge whatever the printer has sent while not being connected
    while(True):
        try:
            endpoint_IN.read(64, timeout=1) # 1 millisecond timeout
        except usb.core.USBTimeoutError:
            break
    
    databuf = b'' # Buffer to split received bytes into lines for octoprint's readline()
    quitDaemon = False      
    while not quitDaemon:
        try:
            if OOPIconn.poll():
                endpoint_OUT.write(OOPIconn.recv_bytes())
        except EOFError: # This happens when the cdcacm_printer (__init__.py) closes the OOPIlistener
            quitDaemon = True
            break
        
        try:
            databuf += endpoint_IN.read(1024, timeout=1).tobytes()
        except usb.core.USBTimeoutError:
            pass
        
        if b'\n' in databuf:
            line, databuf = databuf.split(b'\n', 1)
            line = line+b'\n'
            OIPOconn.send_bytes(line)
            del(line)
            
    OOPIconn.close()
    OIPOconn.close()
    OIPOlistener.close()
    usb.util.release_interface(dev, interface_CDC_Data)
    usb.util.release_interface(dev, interface_CDC_Comm)

fd = int(sys.argv[1])
main(fd)

