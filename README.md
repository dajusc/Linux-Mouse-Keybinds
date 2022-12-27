# Linux-Mouse-Keybinds
Configurable mouse button keybinds for linux. Works for Wine/Proton apps. Features automatic profiles.

## Overview
Binding keyboard keys to the buttons of gaming mouse is essential for some users (like me).
For Windows and Mac the vendors offer configuration software, e.g. "*RAZER Synapse*", "*ROCCAT Swarm*" or "*Logitech Gaming Software*", while they do not offer a linux version.
For linux there are tools like **xbindkeys** and **imwheelrc** which work nice for X-applications, but do unfortunately stop to work as soon as a Wine or Proton (Steam Play) game is started.
[Piper](https://github.com/libratbag/piper) is a very cool project for configuring gaming mouse, but its keybinding functionality just didn't work out for me (e.g. ESC-key can not be assigned).

So I wrote this lightweight keybinder-script in **Python** (no GUI), based on the **evdev** module and **xdotool**.
No installation is required and it works for apps that run in Wine or Proton.
Because a window name or PID can be given in the binding configuration, the script features an fully automatic switching of the keybindings for as many different games as you want.
Also callback functions can be bound to on/off-focus-events, which is usefull for implementing automatic enabling/disabling of mouse accelleration (e.g. via xinput, not part of Linux-Mouse-Keybinds).

## Usage
Rename "*my-lmkb-config.py.TEMPLATE*" to "*my-lmkb-config.py*".
Open "*my-lmkb-config.py*" in a text editor and configure to your needs (help see beow).
Start a terminal (e.g. *bash*), navigate to the scripts directory and type:
```
$> python3 ./my-lmkb-config.py
```
You may now start your game, e.g via Wine or Proton (Steam Play), and leave the script running in the background.
The keybinding stops working as soon as the script exits (ctrl+C) or the terminal is closed.

## Dependencies and Preconditions
Your linux user needs to have access to **evdev**, so e.g. has to be member of the **input** group on Debian based systems.
**Python (2 or 3)** and **xdotool** as well as **readlink (from coreutils)** need to be installed.

## Warnings
- The script does **not unbind** any differently applied bindings or native functions of the mouse buttons. It basically just applies the keystrokes *on top* of the already existing functionality of the buttons.
- It seems possible that **anti cheat** engines for multiplayer games may categorize the actions performed by this script as cheating. So use it in singleplayer only or don't blame me if you get into trouble. ;)

## Configuration tips and examples
Below you can see a configuration example.
If you misconfigure *linuxmousekeybinds* it will give you usefull tips about the allowed settings.
```python
lmkb = linuxmousekeybinds("Logitech G500s Laser Gaming Mouse")

lmkb.bind_key_to_button("Tomb Raider", "BTN_EXTRA",   "3")       # thumb button forward
lmkb.bind_key_to_button("Tomb Raider", "BTN_FORWARD", "c")       # thumb button middle
lmkb.bind_key_to_button("Tomb Raider", "BTN_SIDE",    "Escape")  # thumb button backward
lmkb.bind_key_to_button("Tomb Raider", "REL_HWHEEL+", "r")       # wheel sideways left
lmkb.bind_key_to_button("Tomb Raider", "REL_HWHEEL-", "v")       # wheel sideways right

lmkb.bind_key_to_button(7154, "BTN_SIDE", "3")  # binding by process id (PID)
lmkb.bind_key_to_button("/usr/bin/kate", "BTN_SIDE", "3")  # binding by application binary path
lmkb.bind_key_to_button(None, "BTN_SIDE", "1")  # default binding for all other windows

lmkb.bind_key_to_button("Doom", "BTN_EXTRA", ["1", 500, "2"])  # Macro: "1", 500ms delay, "2"
lmkb.bind_key_to_button("Doom", "BTN_SIDE",  ["3-", 50, "3+"]) # Macro: "3"-keydown, 50ms delay, "3"-keyup
lmkb.bind_key_to_button("Doom", "BTN_SIDE",  [-100, "4"])      # Macro: 70ms to 130ms delay, "3"

def cb1():
    print("Tomb Raider got focus!")
def cb2():
    print("Tomb Raider lost focus!")
lmkb.set_callback_focus_on( "Tomb Raider", cb1) # cb1 will be executed on Tomb Raider getting focus
lmkb.set_callback_focus_off("Tomb Raider", cb2) # cb2 will be executed on Tomb Raider loosing focus

lmkb.run(in_new_thread=False)
```
