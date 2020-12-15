# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import json
import subprocess
import os
import errno
import sys
import signal
import time
import pathlib
from multiprocessing.connection import Listener
from multiprocessing.connection import Client

import octoprint.plugin

class serial_printer(object):
    def __init__(self, comm_instance, port, baudrate, read_timeout):
        self.comm_instance = comm_instance
        self.port = port
        self.baudrate = baudrate
        self.read_timeout = read_timeout
        
        # Get permission firsthand (so that timeouts in communication with serialDaemon do not get triggered by the user taking time to press "yes" on the permission popup)
        subprocess.check_output(['termux-usb', '-r', port])

        # OOPI = Octoprint Out Printer In   
        self.OOPIaddress = ('localhost', 6000)     # family is deduced to be 'AF_INET'
        self.OOPIlistener = Listener(self.OOPIaddress, authkey=b'secret password')
        self.OOPIlistener._listener._socket.settimeout(3)
        
        # Start the Daemon, so that it can attach to OOPIlistener, and open a OIPOlistener
        cdcDaemonpath = str(pathlib.Path(__file__).parent.absolute() / pathlib.Path("serialDaemon.py"))
        self.fd_env = os.environ.copy()
        self.fd_env["TERMUX_CDC_ACM_BAUDRATE"] = str(baudrate)
        self.fd_proc = subprocess.Popen("termux-usb -e "+cdcDaemonpath+" "+port, shell=True, env=self.fd_env, preexec_fn=os.setsid) 
        
        # Accept OOPI connection from Daemon
        self.OOPIconn = self.OOPIlistener.accept()
        
        # Connect to Daemon's OIPOlistener
        self.OIPOaddress = ('localhost', 6001)
        self.OIPOconn = Client(self.OIPOaddress, authkey=b'secret password')
    
    @property
    def timeout(self):
        return self.read_timeout
    
    @timeout.setter
    def timeout(self, value):
        self.read_timeout = value
    
    def write(self, data):
        self.OOPIconn.send_bytes(data)
        return len(data)
        
    def readline(self):
        try:
            if self.OIPOconn.poll(self.read_timeout):
                return self.OIPOconn.recv_bytes()
            else:
                return b''
        except EOFError: # serialClient crashed
            self.close()
            return b''
        
    def close(self):
        try:
            self.OOPIconn.close()
        except AttributeError: # this fails if connection has been closed beforehand (e.g. __del__() after close())
            pass
        try:
            self.OOPIlistener.close()
        except AttributeError:
            pass
        try:
            self.OIPOconn.close()
        except AttributeError:
            pass
        try:
            self.fd_proc.terminate()
        except AttributeError:
            pass
        
    def __del__(self):
        self.close()
        

class Termux_CDC_ACM_Plugin(octoprint.plugin.SettingsPlugin, octoprint.plugin.TemplatePlugin):
    port_names = list()
    
    def serial_printer_factory(self, comm_instance, port, baudrate, read_timeout):
        if not port in self.port_names:
            return None

        serial_obj = serial_printer(
            comm_instance=comm_instance,
            port=port,
            baudrate=baudrate,
            read_timeout=float(read_timeout),
        )
        return serial_obj
    
    
    def get_additional_port_names(self, *args, **kwargs):
        self.port_names = json.loads(subprocess.check_output(['termux-usb', '-l']))
        return self.port_names

__plugin_name__ = "Termux CDC_ACM"
__plugin_version__ = "1.0.0"
__plugin_description__ = "Print from Android if your printer usually shows up as /dev/ttyACM*"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
    plugin = Termux_CDC_ACM_Plugin()

    global __plugin_implementation__
    __plugin_implementation__ = plugin

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.transport.serial.factory": plugin.serial_printer_factory,
        "octoprint.comm.transport.serial.additional_port_names": plugin.get_additional_port_names,
    }
