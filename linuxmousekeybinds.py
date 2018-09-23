# -*- coding: utf-8 -*-
"""
@author: David Schaefer - github@schaeferdavid.de
"""

# If you get an "permission denied" error on start, check which group the devices
# in /dev/input/ belong to (usually "input") and add your user to this group

import sys
import subprocess
import evdev
import select
import natsort
import time
import signal

if (sys.version_info > (3, 0)): # Python3
     import _thread
     thread = _thread
else: # Python2
     import thread


class linuxmousekeybinds():
    def __init__(self, devnam=None, nice=0, delay=0.05, verbose=True):
        self.nice = nice  # Nice value (priority) of process doing the keystroke (xdotool).
        self.delay = delay # Time between key-down and key-up event. Increase if binding only sometimes work.
        self.verbose = verbose  # Print info about whats going on?
        #--
        self.actdevnam = None  # Name of the active device (managed internally).
        self.running = False  # Is the daemon running? (managed internally).
        self.do_stop = True  # Shall the daemon stop running? (managed internally).
        self.bindbypid = False  # False: Do not check for PID, just windowname (managed internally).
        self.evls = {"btn-down": 1,
                     "btn-up": 0,
                     "whl-down": -1,
                     "whl-up": 1,
                     "whl-right": -1,
                     "whl-left": 1}  # Event-value dictionary ().
        #--
        self.devs = {}  # database of all available devices
        self.cfgs = {}  # database of configs
        self.btns = {}  # database buttonname-to-evcode (for the active device)
        #--
        for devpth in natsort.natsorted(evdev.list_devices()):
            dev = evdev.InputDevice(devpth)
            name = dev.name
            ind = 1
            while name in self.devs:
                ind += 1
                name = "{} #{}".format(dev.name, ind)
            self.devs[name] = dev
        #--
        if devnam != None:
            self.select_dev(devnam)
        elif self.verbose:
            print("WARNING: No device set. Must be one of: {}".format(self.devs.keys()))
        #--
        signal.signal(signal.SIGINT, self.stop)

    def __del__(self):
        self.stop()

    def select_dev(self, devnam):
        if devnam in self.devs:
            self.actdevnam = devnam
            self._read_capabilities()
        elif self.verbose:
            print("ERROR: Invalid device name. Must be one of: {}".format(self.devs.keys()))

    def _read_capabilities(self):
        dev = self.devs[self.actdevnam]
        capdict = dev.capabilities(verbose=True)
        caplist = [c for l in capdict.values() for c in l]
        self.btns = {}
        for cap in caplist:
            names, code = cap
            if type(names) != list:
                names = [names]
            for name in names:
                if name.startswith("BTN_") or name.startswith("REL_"):
                    name = name.upper()
                    self.btns[name] = int(code)

    def _to_int(self, string):
        try:
            return int(string)
        except:
            return None

    def bind_key_to_button(self, appnam, btnnam, btndir, keynam, devnam=None):
        if type(appnam) == int:
            appnam = str(appnam)
            self.bindbypid = True
        if devnam == None:
            devnam = self.actdevnam
        evcode = self.btns.get(btnnam, None)
        if evcode == None:
            if self.verbose:
                print("ERROR: Invalid button name. Must be one of: {}".format(self.btns.keys()))
            return
        evvalu = self.evls.get(btndir, None)
        if evvalu == None:
            if self.verbose:
                print("ERROR: Invalid button direction. Must be one of: {}".format(self.evls.keys()))
            return
        #--
        if not devnam in self.cfgs:
            self.cfgs[devnam] = {}
        if not appnam in self.cfgs[devnam]:
            self.cfgs[devnam][appnam] = {}
        if not evcode in self.cfgs[devnam][appnam]:
            self.cfgs[devnam][appnam][evcode] = {}
        if not evvalu in self.cfgs[devnam][appnam][evcode]:
            self.cfgs[devnam][appnam][evcode][evvalu] = {}
        #--
        self.cfgs[devnam][appnam][evcode][evvalu] = keynam

    def _get_keynam(self, appnam, evcode, evvalu, devnam=None):
        if type(appnam) == int:
            appnam = str(appnam)
        if devnam == None:
            devnam = self.actdevnam
        if appnam not in self.cfgs.get(devnam, {}):
            appnam = None  # Default binding settings
        return self.cfgs.get(devnam, {}).get(appnam, {}).get(evcode, {}).get(evvalu, None)

    def _do_keystrokes(self, appind, keynams):
        # print round(time.time()), keynam
        keynams = keynams.split(",")
        for ind, keynam in enumerate(keynams):
            cmd = "nice -n {} xdotool {} --window {} {}".format(self.nice, "{}", appind, keynam)
            subprocess.Popen(cmd.format("keydown"), stdout=subprocess.PIPE, shell=True)
            time.sleep(self.delay)
            subprocess.Popen(cmd.format("keyup"), stdout=subprocess.PIPE, shell=True)
            if ind != len(keynams):
                time.sleep(self.delay)

    def run(self, in_new_thread=True):
        if in_new_thread:
            thread.start_new_thread(self._run, ())
            while not self.running:
                time.sleep(.1)
        else:
            self._run()

    def _run(self):
        if self.verbose:
            print("Linux Mouse Keybinds started!")
        #--
        dev = self.devs[self.actdevnam]
        appind_last = None
        self.do_stop = False
        self.running = True
        try:
            while self.do_stop == False:
                r, w, x = select.select([dev], [], [])
                for event in dev.read():
                    if event.type == evdev.ecodes.EV_KEY or (event.type == evdev.ecodes.EV_REL and event.code not in [0, 1]) or appind_last == None:

                        h = subprocess.Popen("xdotool getactivewindow", stdout=subprocess.PIPE, shell=True)
                        appind = h.stdout.read().decode('utf-8').strip()
                        appind = self._to_int(appind)

                        if appind not in [None, appind_last]:
                            appind_last = appind
                            h = subprocess.Popen("xdotool getwindowpid  {}".format(appind), stdout=subprocess.PIPE, shell=True)
                            apppid = h.stdout.read().decode('utf-8').strip()
                            apppid = self._to_int(apppid)
                            h = subprocess.Popen("xdotool getwindowname {}".format(appind), stdout=subprocess.PIPE, shell=True)
                            appnam = h.stdout.read().decode('utf-8').strip()
                            if self.verbose and appnam != "":
                                appnam = appnam.encode('ascii', 'ignore').decode('utf-8')
                                print("Active window changed to \"{}\" (PID: {})".format(appnam, apppid))

                        keynams = self._get_keynam(appnam, event.code, event.value) # binding based on windowname
                        if keynams == None and self.bindbypid:
                            keynams = self._get_keynam(apppid, event.code, event.value) # binding based on PID
                        if keynams != None:
                            self._do_keystrokes(appind, keynams)
        finally:
            self.running = False
        if self.verbose:
            print("Linux Mouse Keybinds stopped!")

    def stop(self, signum=None, sigframe=None):
        self.do_stop = True

    def is_running(self):
        return self.running == True


if __name__ == "__main__":
    print("######################################################################")

    lmkb = linuxmousekeybinds("Logitech G500s Laser Gaming Mouse")
    #--
    lmkb.bind_key_to_button("Rise of the Tomb Raider™", "BTN_EXTRA",   "btn-down", "3")  # thumb button forward
    lmkb.bind_key_to_button("Rise of the Tomb Raider™", "BTN_FORWARD", "btn-down", "c")  # thumb button middle
    lmkb.bind_key_to_button("Rise of the Tomb Raider™", "BTN_SIDE",    "btn-down", "Escape")  # thumb button backward
    lmkb.bind_key_to_button("Rise of the Tomb Raider™", "REL_HWHEEL",  "whl-left", "r")  # wheel sideways left
    lmkb.bind_key_to_button("Rise of the Tomb Raider™", "REL_HWHEEL",  "whl-right", "v")  # wheel sideways right
    #--
    lmkb.bind_key_to_button("EthanCarter (64-bit, PCD3D_SM5)", "BTN_SIDE", "btn-down", "Escape")  # thumb button backward
    #--
    lmkb.bind_key_to_button("Spyder (Python 2.7)", "BTN_SIDE", "btn-down", "4,2") # sequential keypresses
    lmkb.bind_key_to_button(2726, "BTN_SIDE", "btn-down", "e") 
    #--
    lmkb.run()
    #--
    while lmkb.is_running():
        time.sleep(.1)

#    #-- EXAMPLES --
#    lmkb = linuxmousekeybinds("Logitech USB Optical Mouse") # RX 1000
#    #--
#    lmkb.bind_key_to_button(None, "BTN_EXTRA",   "btn-down",  "1") # thumb button forward
#    lmkb.bind_key_to_button(None, "BTN_FORWARD", "btn-down",  "2") # thumb button middle
#    lmkb.bind_key_to_button(None, "BTN_SIDE",    "btn-down",  "3") # thumb button backward
#    lmkb.bind_key_to_button(None, "REL_HWHEEL",  "whl-left",  "4") # wheel sideways left
#    lmkb.bind_key_to_button(None, "REL_HWHEEL",  "whl-right", "5") # wheel sideways right
#    lmkb.bind_key_to_button(None, "REL_WHEEL",   "whl-up",    "6") # wheel up
#    lmkb.bind_key_to_button(None, "REL_WHEEL",   "whl-down",  "7") # wheel down
#    #--
#    lmkb.bind_key_to_button(7154, "BTN_SIDE", "btn-down", "3") # Binding by PID instead of window-name
#    #--
#    lmkb.bind_key_to_button("Rise of the Tomb Raider™", "BTN_EXTRA",   "btn-down", "1") # thumb button forward
#    lmkb.bind_key_to_button("Rise of the Tomb Raider™", "BTN_FORWARD", "btn-down", "2") # thumb button middle
#    lmkb.bind_key_to_button("Rise of the Tomb Raider™", "BTN_SIDE",    "btn-down", "Escape") # thumb button backward
