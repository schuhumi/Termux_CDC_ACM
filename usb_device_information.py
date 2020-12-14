#!/usr/bin/env python3

import usb.core
import usb.util
import usb.control
from usblib import device_from_fd
import sys
import array
import os
import time
import json
import subprocess

def iter_devices():
    port_names = json.loads(subprocess.check_output(['termux-usb', '-l']))
    for p in port_names:
        print(f"port: {p}")
        print(subprocess.check_output(["termux-usb", "-r", "-e", __file__, str(p)]).decode("utf-8"))


def usb_info(fd):
    dev = device_from_fd(fd)
    print(f"{hex(dev.idVendor)=}, {hex(dev.idProduct)=}")
    cfg = dev.get_active_configuration()
    print(cfg)


if len(sys.argv)>1:
    fd = int(sys.argv[1])
    usb_info(fd)
else:
    iter_devices()

