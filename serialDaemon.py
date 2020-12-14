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
from serialCDCACM import check_is_CDCACM, serial_CDCACM

def main(fd, debug=False):
    dev = device_from_fd(fd)
    
    if dev.is_kernel_driver_active(0):
        dev.detach_kernel_driver(0)
        print("kernel driver detached")
    else:
        print("no kernel driver attached")
     
    # Configure usb-serial-converter
    baudrate = int(os.environ["TERMUX_CDC_ACM_BAUDRATE"]) # From environment variable
    
    serial = None
    if check_is_CDCACM(dev):
        serial = serial_CDCACM(dev=dev, baudrate=baudrate)
        
    if serial is None:
        print(f"Couldn't find matching driver for usb device {hex(dev.idVendor)=}, {hex(dev.idProduct)=} !")
        print(dev.get_active_configuration())
        return
    
    # Create Ocotoprint-In-Printer-Out-listener for octoprint to attach to
    OIPOaddress = ('localhost', 6001)     # family is deduced to be 'AF_INET'
    OIPOlistener = Listener(OIPOaddress, authkey=b'secret password')
    
    # Connect to Octoprint-Out-Printer-In-listener of octoprint
    OOPIaddress = ('localhost', 6000)
    OOPIconn = Client(OOPIaddress, authkey=b'secret password')
    
    # Accept connection of octoprint on OIPOlistener
    OIPOconn = OIPOlistener.accept()
    
    
    
    databuf = b'' # Buffer to split received bytes into lines for octoprint's readline()
    quitDaemon = False      
    while not quitDaemon:
        try:
            if OOPIconn.poll():
                serial.write(OOPIconn.recv_bytes())
        except EOFError: # This happens when the cdcacm_printer (__init__.py) closes the OOPIlistener
            quitDaemon = True
            break
        
        databuf += serial.read()
        
        if b'\n' in databuf:
            line, databuf = databuf.split(b'\n', 1)
            line = line+b'\n'
            OIPOconn.send_bytes(line)
            del(line)
            
    OOPIconn.close()
    OIPOconn.close()
    OIPOlistener.close()
    serial.close()
    

fd = int(sys.argv[1])
main(fd)

