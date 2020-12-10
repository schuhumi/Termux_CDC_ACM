#!/usr/bin/env python3

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

CDC_COMM_INTF = 0
CDC_DATA_INTF = 1
EP_IN = 0x81
EP_OUT = 0x03

tr_data = {}
tr_last = time.time()
def timereport(name, t):
    global tr_data
    global tr_last
    if name in tr_data:
        tr_data[name] += t
    else:
        tr_data[name] = t
        
    if time.time()-tr_last > 3:
        tr_last = time.time()
        for k,v in tr_data.items():
            print(k, v)


def main(fd, debug=False):
    dev = device_from_fd(fd)
    
    # Lock usb device
    usb.util.claim_interface(dev, CDC_DATA_INTF)
    usb.util.claim_interface(dev, CDC_COMM_INTF)
    
    # Get endpoint
    cfg = dev.get_active_configuration()
    print(cfg)
    intf = cfg[(1, 0)]
    ep_in = intf[0]
    
    # Configure usb-serial-converter
    baudrate = int(os.environ["TERMUX_CDC_ACM_BAUDRATE"])
    serialConf = bytearray(list((baudrate).to_bytes(length=6, byteorder="little")) + [0x08])
    dev.ctrl_transfer(0x21, 0x22, 0x01 | 0x02, 0, None)
    dev.ctrl_transfer(0x21, 0x20, 0, 0, serialConf)
    
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
            dev.read(EP_IN, 64, timeout=1) # 1 millisecond timeout
        except usb.core.USBTimeoutError:
            break
    
    databuf = b'' # Buffer to split received bytes into lines for octoprint's readline()
    quitDaemon = False      
    while not quitDaemon:
        try:
            if OOPIconn.poll():
                dev.write(EP_OUT, OOPIconn.recv_bytes())
        except EOFError: # This happens when the cdcacm_printer (__init__.py) closes the OOPIlistener
            quitDaemon = True
            break
        
        try:
            databuf += dev.read(EP_IN, 1024, timeout=1).tobytes()
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

fd = int(sys.argv[1])
main(fd)

