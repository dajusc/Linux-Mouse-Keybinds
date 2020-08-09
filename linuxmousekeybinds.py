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
import random

if (sys.version_info > (3, 0)): # Python3
     import _thread
     thread = _thread
else: # Python2
     import thread


class linuxmousekeybinds():
    def __init__(self, devnam=None, nice=0, delay=0.05, verbose=True, debug=False):
        self.nice = nice  # Nice value (priority) of process doing the keystroke (xdotool).
        self.delay = delay # Time between key-down and key-up event. Increase if binding only sometimes work.
        self.verbose = verbose  # Print info about whats going on?
        self.debug = debug  # Print debug info
        #--
        self.actdevnam = None  # Name of the active device (managed internally).
        self.running = False  # Is the daemon running? (managed internally).
        self.do_stop = True  # Shall the daemon stop running? (managed internally).
        self.bindbypid = False  # False: Do not check for PID, just windowname (managed internally).
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
            print("ERROR: Invalid device name \"{}\". Must be one of: {}".format(devnam, self.devs.keys()))

    def _read_capabilities(self):
        if self.actdevnam is None:
            return
        dev = self.devs[self.actdevnam]
        capdict = dev.capabilities(verbose=True)
        caplist = [c for l in capdict.values() for c in l]
        self.btns = {}
        for cap in caplist:
            names, code = cap
            if type(names) != list:
                names = [names]
            for name in names:
                name = name.upper()
                if name.startswith("BTN_"):
                    self.btns[name] = int(code)
                if name.startswith("REL_"):
                    self.btns[name + "+"] = +int(code)
                    self.btns[name + "-"] = -int(code)

    def bind_key_to_button(self, appnam, btnnam, keynam, devnam=None):
        if devnam == None:
            devnam = self.actdevnam
        if devnam is None:
            return
        if keynam is None:
            return
        if type(appnam) == int:
            appnam = str(appnam)
            self.bindbypid = True
        evcode = self.btns.get(btnnam, None)
        if evcode == None:
            if self.verbose:
                print("ERROR: Invalid button name \"{}\". Must be one of: {}".format(btnnam, self.btns.keys()))
            return
        #--
        if not devnam in self.cfgs:
            self.cfgs[devnam] = {}
        if not appnam in self.cfgs[devnam]:
            self.cfgs[devnam][appnam] = {}
        if not evcode in self.cfgs[devnam][appnam]:
            self.cfgs[devnam][appnam][evcode] = {}
        #--
        self.cfgs[devnam][appnam][evcode] = keynam

    def _get_keynam(self, appnam, evcode, devnam=None):
        if devnam == None:
            devnam = self.actdevnam
        if devnam is None:
            return
        if type(appnam) == int:
            appnam = str(appnam)
        for _appnam in [appnam, None]: # None = default binding settings
            keynam = self.cfgs.get(devnam, {}).get(_appnam, {}).get(evcode, None)
            if keynam is not None:
                return keynam

    def _do_key(self, appind, keynam, down=True, up=True):
        cmd = "nice -n {} xdotool {} --window {} {}".format(self.nice, "{}", appind, keynam)
        if down:
            subprocess.Popen(cmd.format("keydown"), stdout=subprocess.PIPE, shell=True)
        if down and up:
            time.sleep(self.delay)
        if up:
            subprocess.Popen(cmd.format("keyup"), stdout=subprocess.PIPE, shell=True)

    def _do_macro(self, appind, macro):
        for command in macro:
            if type(command) in [int, float]: # delay in milliseconds
                if command < 0:
                    command *= -(0.3 * (1-2*random.random())+1) # +/- 30% random deviation of given value
                time.sleep(1e-3 * command)
            elif type(command) in [str]: # keydown or keyup or keydown+up
                keynam = command
                down = ("-" in keynam)
                up   = ("+" in keynam)
                if not up and not down:
                    up = down = True
                keynam = keynam.strip("-+")
                self._do_key(appind, keynam, down, up)

    def _set_callback_focus_on_off(self, appnam, cbfunc, typ, devnam=None):
        if devnam == None:
            devnam = self.actdevnam
        if devnam is None:
            return
        if not devnam in self.cfgs:
            self.cfgs[devnam] = {}
        if not appnam in self.cfgs[devnam]:
            self.cfgs[devnam][appnam] = {}
        self.cfgs[devnam][appnam][typ] = cbfunc

    def set_callback_focus_on(self, appnam, cbfunc, devnam=None):
        self._set_callback_focus_on_off(appnam, cbfunc, "callback_focus_on", devnam)

    def set_callback_focus_off(self, appnam, cbfunc, devnam=None):
        self._set_callback_focus_on_off(appnam, cbfunc, "callback_focus_off", devnam)

    def _do_callback_focus_on_off(self, appnam, typ, devnam=None):
        if devnam == None:
            devnam = self.actdevnam
        if devnam is None:
            return
        cbfunc = self.cfgs.get(devnam, {}).get(appnam, {}).get(typ, None)
        if cbfunc != None:
            cbfunc()

    def _do_callback_focus_on(self, appnam, devnam=None):
        self._do_callback_focus_on_off(appnam, "callback_focus_on", devnam=None)

    def _do_callback_focus_off(self, appnam, devnam=None):
        self._do_callback_focus_on_off(appnam, "callback_focus_off", devnam=None)

    def _to_int(self, string):
        try:
            return int(string)
        except:
            return None

    def _get_active_window_index(self):
        h = subprocess.Popen("xdotool getactivewindow", stdout=subprocess.PIPE, shell=True)
        h.wait()
        appind = h.stdout.read().decode('utf-8').strip()
        appind = self._to_int(appind)
        #--
        return appind

    def _get_window_name_and_pid(self, appind):
        h = subprocess.Popen("xdotool getwindowname {}".format(appind), stdout=subprocess.PIPE, shell=True)
        h.wait()
        appnam = h.stdout.read().decode('utf-8').strip()
        appnam = appnam.encode('ascii', 'ignore').decode('utf-8')
        #--
        h = subprocess.Popen("xdotool getwindowpid  {}".format(appind), stdout=subprocess.PIPE, shell=True)
        h.wait()
        apppid = h.stdout.read().decode('utf-8').strip()
        apppid = self._to_int(apppid)
        #--
        return (appnam, apppid)

    def run(self, in_new_thread=True):
        if self.actdevnam is None:
            return
        if in_new_thread:
            thread.start_new_thread(self._run, ())
            while not self.running:
                time.sleep(.1)
        else:
            self._run()

    def _run(self):
        if self.verbose:
            print("Linux Mouse Keybinds started!")
        if self.debug:
            print("DEBUG: Devices: {}".format(list(self.devs.keys())))
            print("DEBUG: Buttons: {}".format(list(self.btns.keys())))
        #--
        EV_KEY = evdev.ecodes.EV_KEY
        EV_REL = evdev.ecodes.EV_REL
        dev = self.devs[self.actdevnam]
        appind_last = None
        appnam_last = None
        self.do_stop = False
        self.running = True
        try:
            while self.do_stop == False:
                r, w, x = select.select([dev], [], [])
                for event in dev.read():
                    evtype = event.type
                    evcode = event.code
                    evvalu = event.value

                    if (evtype not in [EV_KEY, EV_REL]) or (evtype == EV_REL and evcode in [0, 1]):
                        continue
                    if (evtype == EV_REL):
                        evcode *= evvalu

                    appind = self._get_active_window_index()
                    if appind not in [None, appind_last]:
                        self._do_callback_focus_off(appnam_last)
                        #--
                        appnam, apppid = self._get_window_name_and_pid(appind)
                        if self.verbose and appnam != "":
                            print("Active window changed to \"{}\" (PID: {})".format(appnam, apppid))
                        #--
                        self._do_callback_focus_on(appnam)
                    appind_last = appind
                    appnam_last = appnam

                    keynam = self._get_keynam(appnam, evcode) # binding based on windowname
                    if keynam == None and self.bindbypid:
                        keynam = self._get_keynam(apppid, evcode) # binding based on PID

                    if self.debug:
                        print("DEBUG: evtype:{}, evcode:{}, evvalu:{}, keynam:{}".format(evtype, evcode, evvalu, keynam))

                    if keynam != None:
                        down = (evtype == EV_KEY and evvalu == 1) or (evtype == EV_REL)
                        up   = (evtype == EV_KEY and evvalu == 0) or (evtype == EV_REL)
                        if type(keynam) == list and down:
                            self._do_macro(appind, macro=keynam)
                        elif type(keynam) == str:
                            self._do_key(appind, keynam, down, up)
        finally:
            self.running = False
        if self.verbose:
            print("Linux Mouse Keybinds stopped!")

    def stop(self, signum=None, sigframe=None):
        self.do_stop = True

    def is_running(self):
        return self.running == True


if __name__ == "__main__":
    # As an alternative to using a separate configuration file, the config could be done right here
    pass