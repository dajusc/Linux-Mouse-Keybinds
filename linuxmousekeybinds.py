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
    def __init__(self, devnams=None, nice=0, delay=0.05, exact=False, verbose=True, debug=False):
        self.devnams   = devnams  # Name of the device (Or list of alias names)
        self.nice      = nice     # Nice value (priority) of process doing the keystroke (xdotool).
        self.delay     = delay    # Time between key-down and key-up event. Increase if binding only sometimes work.
        self.verbose   = verbose  # Print info about whats going on?
        self.exact     = exact    # Bind only if window title exactly matches the application name?
        self.debug     = debug    # Print debug info
        #--
        self.devnam    = None   # Name of the active device
        self.dev       = None   # Active device
        self.running   = False  # Is the daemon running?
        self.do_stop   = False  # Shall the daemon stop running?
        self.bindbypid = False  # False: Do not check for PID, just windowname
        self.dct_abk   = {}     # database mapping appname + btnname to keyname
        self.dct_aek   = {}     # database mapping appname + evcode  to keyname
        #--
        signal.signal(signal.SIGINT, self.stop)
        #--
        if type(self.devnams) not in (list, set, tuple):
            self.devnams = (self.devnams,)


    def __del__(self):
        self.stop()


    def bind_key_to_button(self, appnam, btnnam, keynam):
        if keynam is None:
            return
        if type(appnam) == int:
            appnam = str(appnam)
            self.bindbypid = True
        #--
        if not appnam in self.dct_abk:
            self.dct_abk[appnam] = {}
        self.dct_abk[appnam][btnnam] = keynam


    def _get_available_devs(self): # get dict with all available devices
        devs = {}
        for devpth in natsort.natsorted(evdev.list_devices()):
            dev  = evdev.InputDevice(devpth)
            name = dev.name
            ind  = 1
            while name in devs:
                ind += 1
                name = "{} #{}".format(dev.name, ind)
            devs[name] = dev
        return devs


    def _read_capabilities(self):
        dev = self.dev
        capdict = dev.capabilities(verbose=True)
        caplist = [c for l in capdict.values() for c in l]
        btns = {}
        for cap in caplist:
            names, code = cap
            if type(names) != list:
                names = [names]
            for name in names:
                name = name.upper()
                if name.startswith("BTN_"):
                    btns[name] = int(code)
                if name.startswith("REL_"):
                    btns[name + "+"] = +int(code)
                    btns[name + "-"] = -int(code)
        #--
        self.dct_aek = {}
        for appnam in self.dct_abk:
            if not appnam in self.dct_aek:
                self.dct_aek[appnam] = {}
            for btnnam in self.dct_abk[appnam]:
                if btnnam in btns:
                    evcode = btns[btnnam]
                    self.dct_aek[appnam][evcode] = self.dct_abk[appnam][btnnam]
        if self.debug:
            print(self.dct_aek)


    def _connect_dev(self, devnam):
        devs = self._get_available_devs()
        if not devnam in devs:
            return False
        self.dev    = devs[devnam]
        self.devnam = devnam
        self._read_capabilities()
        return True


    def _get_keynam(self, appnam, evcode):
        if type(appnam) == int:
            appnam = str(appnam)
        for _appnam in [appnam, None]: # None = default binding settings
            keynam = self.dct_aek.get(_appnam, {}).get(evcode, None)
            if keynam is not None:
                return keynam


    def _do_key(self, winind, keynam, down=True, up=True):
        cmd = "nice -n {} xdotool {} --window {} {}".format(self.nice, "{}", winind, keynam)
        if down:
            subprocess.Popen(cmd.format("keydown"), stdout=subprocess.PIPE, shell=True)
        if down and up:
            time.sleep(self.delay)
        if up:
            subprocess.Popen(cmd.format("keyup"), stdout=subprocess.PIPE, shell=True)


    def _do_macro(self, winind, macro):
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
                self._do_key(winind, keynam, down, up)


    def _set_callback_focus_on_off(self, appnam, cbfunc, typ):
        if not appnam in self.dct_aek:
            self.dct_aek[appnam] = {}
        self.dct_aek[appnam][typ] = cbfunc


    def set_callback_focus_on(self, appnam, cbfunc):
        self._set_callback_focus_on_off(appnam, cbfunc, "callback_focus_on")


    def set_callback_focus_off(self, appnam, cbfunc):
        self._set_callback_focus_on_off(appnam, cbfunc, "callback_focus_off")


    def _do_callback_focus_on_off(self, appnam, typ):
        cbfunc = self.dct_aek.get(appnam, {}).get(typ, None)
        if cbfunc != None:
            cbfunc()


    def _do_callback_focus_on(self, appnam):
        self._do_callback_focus_on_off(appnam, "callback_focus_on")


    def _do_callback_focus_off(self, appnam):
        self._do_callback_focus_on_off(appnam, "callback_focus_off")


    def _to_int(self, string):
        try:
            return int(string)
        except:
            return None


    def _get_active_window_index(self):
        h = subprocess.Popen("xdotool getactivewindow", stdout=subprocess.PIPE, shell=True)
        h.wait()
        winind = h.stdout.read().decode('utf-8').strip()
        winind = self._to_int(winind)
        #--
        return winind


    def _get_application_name_and_pid(self, winind):
        h = subprocess.Popen("xdotool getwindowpid {}".format(winind), stdout=subprocess.PIPE, shell=True)
        h.wait()
        apppid = h.stdout.read().decode('utf-8').strip()
        apppid = self._to_int(apppid)
        #--
        h = subprocess.Popen("xdotool getwindowname {}".format(winind), stdout=subprocess.PIPE, shell=True)
        h.wait()
        appnam = h.stdout.read().decode('utf-8').strip()
        appnam = appnam.encode('ascii', 'ignore').decode('utf-8')
        if not self.exact:
            done = (appnam in self.dct_aek)
            if not done:
                h = subprocess.Popen("readlink -f /proc/{}/exe".format(apppid), stdout=subprocess.PIPE, shell=True)
                h.wait()
                apppth = h.stdout.read().decode('utf-8').strip()
                apppth = apppth.encode('ascii', 'ignore').decode('utf-8')
                if apppth in self.dct_aek:
                    appnam = apppth
                    done   = True
            if not done:
                for cfg_appnam in self.dct_aek:
                    if appnam.startswith(cfg_appnam):
                        appnam = cfg_appnam
                        done   = True
                        break
            if not done:
                for cfg_appnam in self.dct_aek:
                    if appnam.lower() in cfg_appnam.lower() or cfg_appnam.lower() in appnam.lower():
                        appnam = cfg_appnam
                        done   = True
                        break
        #--
        return (appnam, apppid)


    def run(self, in_new_thread=False):
        if in_new_thread:
            thread.start_new_thread(self._run, ())
        else:
            self._run()


    def _run(self, in_new_thread=True):
        is_reconnect = False
        if self.verbose:
            print("Linux Mouse Keybinds started!")
        while self.do_stop == False:
            for devnam in self.devnams:
                if self._connect_dev(devnam):
                    if is_reconnect:
                        if self.verbose: # device got (temporarily) unconnected
                            print("Active device got reconnected!")
                    else:
                        is_reconnect = True
                    self.__run()
            if self.do_stop == False:
                time.sleep(1) # retry reconnecting in 1 sec
        if self.verbose:
            print("Linux Mouse Keybinds stopped!")


    def __run(self):
        EV_KEY = evdev.ecodes.EV_KEY
        EV_REL = evdev.ecodes.EV_REL
        winind_last = None
        appnam_last = None
        self.running = True
        try:
            while self.do_stop == False:
                r, w, x = select.select([self.dev], [], [])
                for event in self.dev.read():
                    evtype = event.type
                    evcode = event.code
                    evvalu = event.value

                    if (evtype not in [EV_KEY, EV_REL]) or (evtype == EV_REL and evcode in [0, 1]):
                        continue
                    if (evtype == EV_REL):
                        evcode *= evvalu

                    winind = self._get_active_window_index()
                    if winind not in [None, winind_last]:
                        self._do_callback_focus_off(appnam_last)
                        #--
                        appnam, apppid = self._get_application_name_and_pid(winind)
                        if self.verbose and appnam != "":
                            print("Active application changed to \"{}\" (PID: {})".format(appnam, apppid))
                        #--
                        self._do_callback_focus_on(appnam)
                    winind_last = winind
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
                            self._do_macro(winind, macro=keynam)
                        elif type(keynam) == str:
                            self._do_key(winind, keynam, down, up)

        except OSError as exc:
            if self.verbose and exc.strerror == "No such device": # device got (temporarily) unconnected
                print("Active device got disconnected! Waiting for reconnect...")
        finally:
            self.running = False


    def stop(self, signum=None, sigframe=None):
        self.do_stop = True


    def is_running(self):
        return self.running == True


if __name__ == "__main__":
    # As an alternative to using a separate configuration file, the config could be done right here
    pass