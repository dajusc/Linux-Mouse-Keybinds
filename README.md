# Linux-Mouse-Keybinds
Configurable mouse button keybinds for linux. Works for Wine/Proton apps. Features automatic profiles.

## Overview
Binding keyboard keys to the buttons of gaming mouse is essential for some users (like me).
For Windows and Mac the vendors offer configuration software, e.g. "*RAZER Synapse*", "*ROCCAT Swarm*" or "*Logitech Gaming Software*", while they do not offer a linux version.
For linux there are tools like **xbindkeys** and **imwheelrc** which work nice for X-applications, but do unfortunately stop to work as soon as a Wine or Proton (Steam Play) game is started.
[Piper](https://github.com/libratbag/piper) is a very cool project for configuring gaming mouse, but its keybinding functionality just didn't work out for me (e.g. ESC-key can not be assigned).

So I wrote this lightweight keybinder-script in **Python** (no GUI), based on the **evdev** module and **xdotool**.
No installation is required and it works in Wine or Proton.
Because a window name or PID can be given in the binding configuration, the script features an fully automatic switching of the keybindings for as many different games as you want.

## Usage
Open "*linuxmousekeybinds.py*" in a text editor, scroll to the bottom and configure to your needs (help see beow).
Then start a terminal (e.g. *bash*) navigate to the scripts directory and type:
```
$> python ./linuxmousekeybinds.py
```
You may now start your game, e.g via Wine or Proton (Steam Play), and leave the script running in the background.
The keybinding stops working as soon as the script exits (ctrl+C) or the terminal is closed.

## Warnings
- The script does **not unbind** any differently applied bindings or native functions of the mouse buttons. It basically just applies the keystrokes *on top* of the already existing functionality of the buttons.
- It seems possible that **anti cheat** engines for multiplayer games may categorize the actions performed by this script as cheating. So use it in singleplayer only or don't blame me if you get into trouble. ;)

## Configuration tips and examples
Below you can see a configuration example.
If you misconfigure *linuxmousekeybinds* it will give you usefull tips about the allowed settings.
```python
lmkb = linuxmousekeybinds("Logitech G500s Laser Gaming Mouse")

lmkb.bind_key_to_button("Rise of the Tomb Raider", "BTN_EXTRA",   "3")       # thumb button forward
lmkb.bind_key_to_button("Rise of the Tomb Raider", "BTN_FORWARD", "c")       # thumb button middle
lmkb.bind_key_to_button("Rise of the Tomb Raider", "BTN_SIDE",    "Escape")  # thumb button backward
lmkb.bind_key_to_button("Rise of the Tomb Raider", "REL_HWHEEL+", "r")       # wheel sideways left
lmkb.bind_key_to_button("Rise of the Tomb Raider", "REL_HWHEEL-", "v")       # wheel sideways right

lmkb.bind_key_to_button(7154, "BTN_SIDE", "3")  # binding by PID instead of window-name
lmkb.bind_key_to_button(None, "BTN_SIDE", "1")  # default binding for any other window

lmkb.run()
while lmkb.is_running():
    time.sleep(.1)
```
