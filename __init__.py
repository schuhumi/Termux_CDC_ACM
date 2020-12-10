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

class cdcacm_printer(object):
    def __init__(self, comm_instance, port, baudrate, read_timeout):
        self.comm_instance = comm_instance
        self.port = port
        self.baudrate = baudrate
        self.read_timeout = read_timeout

        # OOPI = Octoprint Out Printer In   
        self.OOPIaddress = ('localhost', 6000)     # family is deduced to be 'AF_INET'
        self.OOPIlistener = Listener(self.OOPIaddress, authkey=b'secret password')
        
        # Start the Daemon, so that it can attach to OOPIlistener, and open a OIPOlistener
        cdcDaemonpath = str(pathlib.Path(__file__).parent.absolute() / pathlib.Path("cdcDaemon.py"))
        self.fd_env = os.environ.copy()
        self.fd_env["TERMUX_CDC_ACM_BAUDRATE"] = str(baudrate)
        self.fd_proc = subprocess.Popen("termux-usb -r -e "+cdcDaemonpath+" "+port, shell=True, env=self.fd_env, preexec_fn=os.setsid) 
        
        # Accept OOPI connection from Daemon
        self.OOPIconn = self.OOPIlistener.accept()
        
        # Connect to Daemon's OIPOlistener
        self.OIPOaddress = ('localhost', 6001)
        self.OIPOconn = Client(self.OIPOaddress, authkey=b'secret password')
        
    def write(self, data):
        self.OOPIconn.send_bytes(data)
        
    def readline(self):
        if self.OIPOconn.poll():
            return self.OIPOconn.recv_bytes()
        else:
            return b''
        
    def close(self):
        self.OOPIconn.close()
        self.OOPIlistener.close()
        self.OIPOconn.close()
        os.killpg(os.getpgid(self.fd_proc.pid), signal.SIGTERM)
        

class Termux_CDC_ACM_Plugin(octoprint.plugin.SettingsPlugin, octoprint.plugin.TemplatePlugin):
    port_names = list()
    
    def cdcacm_printer_factory(self, comm_instance, port, baudrate, read_timeout):
        if not port in self.port_names:
            return None

        serial_obj = cdcacm_printer(
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
        "octoprint.comm.transport.serial.factory": plugin.cdcacm_printer_factory,
        "octoprint.comm.transport.serial.additional_port_names": plugin.get_additional_port_names,
    }
