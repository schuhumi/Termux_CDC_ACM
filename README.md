# Termux_CDC_ACM

Octoprint Plugin to print to tty **<u>ACM</u>** devices on Android through libusb in Termux. It uses libusb and a cdc-acm-driver written in Python.

**This als ALPHA!**

usblib.py is taken from [GitHub - Querela/termux-usb-python: USB access with Python on Termux (Android)](https://github.com/Querela/termux-usb-python)

# How to use

#### 1. Install Termux and Termux:API apps
 - [https://play.google.com/store/apps/details?id=com.termux](https://play.google.com/store/apps/details?id=com.termux)
 - [https://play.google.com/store/apps/details?id=com.termux.api](https://play.google.com/store/apps/details?id=com.termux.api)

#### 2. Inside Termux:

```shell
pkg install python termux-api libusb pyusb pyftdi clan git
pip install octoprint
```

#### 3. Make sure your printer connection works

```shell
termux-usb -l
```

should show something like `/dev/bus/usb/001/011`when the printer is connected (usually via an USB-OTG adapter)

#### 4. Test if Octoprint works

first you can check your current ip using

```shell
ip addr
```

then start octoprint like this.

```shell
octoprint serve
```

If octoprint works correctly on `http://<ip-addr>:5000`, stop it again with Ctrl+C

#### 5. Install the plugin

```shell
cd ~/.octoprint/plugins
git clone https://github.com/schuhumi/Termux_CDC_ACM/
```

#### 6. Start Octoprint again

```shell
octoprint serve
```

You should now see an entry similar to` /dev/bus/usb/001/011` in the serialport dropdown menu in Octoprint's webinterface. Choose it and also choose the correct baudrate, then click connect. Now a popup should appear on your Android device asking for Termux's permission to access the usb device, choose yes. Octoprint should now connect to your printer.
