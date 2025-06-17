import uinput
import time
import evdev
from evdev import InputDevice, categorize, ecodes
from evdev import UInput, ecodes as e
import threading
from threading import Thread
import sys
from PyQt5 import QtCore, QtWidgets, QtGui

device_path = '/dev/input/event5'  # You can find this with `evtest`

key_events = [
    uinput.KEY_A, uinput.KEY_B, uinput.KEY_C, uinput.KEY_D, uinput.KEY_E,
    uinput.KEY_F, uinput.KEY_G, uinput.KEY_H, uinput.KEY_I, uinput.KEY_J,
    uinput.KEY_K, uinput.KEY_L, uinput.KEY_M, uinput.KEY_N, uinput.KEY_O,
    uinput.KEY_P, uinput.KEY_Q, uinput.KEY_R, uinput.KEY_S, uinput.KEY_T,
    uinput.KEY_U, uinput.KEY_V, uinput.KEY_W, uinput.KEY_X, uinput.KEY_Y,
    uinput.KEY_Z,

    uinput.KEY_ENTER,
    uinput.KEY_COMMA,
    uinput.KEY_DOT,
    uinput.KEY_SLASH
]

mouse_events = {
    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT],
    e.EV_REL: [e.REL_X, e.REL_Y],
}

keyboard = uinput.Device(key_events)
mouse = UInput(mouse_events, name="Logitech G502 HERO SE", version=0x3)

time.sleep(1)  # wait for device to register

def left_click():
    mouse.write(e.EV_KEY, e.BTN_LEFT, 1)
    mouse.syn()
    time.sleep(0.05)
    mouse.write(e.EV_KEY, e.BTN_LEFT, 0)
    mouse.syn()

def place_tower():
    keyboard.emit_click(uinput.KEY_Z)
    time.sleep(0.05)
    left_click()
    time.sleep(0.05)
    mouse.write(e.EV_REL, e.REL_Y, -10)
    mouse.syn()
    time.sleep(0.05)
    left_click()
    time.sleep(0.1)

def upgrade_tower():
    for i in range(2):
        keyboard.emit_click(uinput.KEY_DOT)
        time.sleep(0.05)
    for i in range(2):
        keyboard.emit_click(uinput.KEY_SLASH)
        time.sleep(0.05)

def listen_for_keypress():
    dev = InputDevice(device_path)
    print(f"Listening on {dev.name} ({device_path})")

    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            if key_event.keycode == 'KEY_F9' and key_event.keystate == 0:
                place_tower()
                upgrade_tower()

class Overlay(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Tool  # Makes window not appear in taskbar
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)  # Click-through

        self.label = QtWidgets.QLabel("Mode: 1", self)
        self.label.setStyleSheet("color: white; font-size: 24px; background: rgba(0,0,0,0.5); padding: 10px;")
        self.label.move(50, 50)

        self.resize(200, 100)

    def update_mode(self, mode_num):
        self.label.setText(f"Mode: {mode_num}")

if __name__ == "__main__":
    try:
        app = QtWidgets.QApplication(sys.argv)
        overlay = Overlay()
        overlay.show()

        def update_loop():
            mode = 1
            while True:
                time.sleep(2)
                mode = (mode % 3) + 1
                QtCore.QMetaObject.invokeMethod(overlay, "update_mode", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(int, mode))

        Thread(target=update_loop, daemon=True).start()
        # listen_for_keypress()
    except KeyboardInterrupt:
        print("Goodbye!")
    sys.exit(app.exec_())
