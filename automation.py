import uinput
import time
import asyncio
import evdev
import queue
from evdev import InputDevice, categorize, ecodes
from evdev import UInput, ecodes as e
import threading
from threading import Thread
import sys
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtGui import QPalette, QColor
import signal

event_queue = queue.Queue()

global app, overlay

device_paths = [('/dev/input/event1', {"KEY_F20", "KEY_F24"}), ('/dev/input/event22', {}), ('/dev/input/event5', {})]

key_events = [
    uinput.KEY_A, uinput.KEY_B, uinput.KEY_C, uinput.KEY_D, uinput.KEY_E,
    uinput.KEY_F, uinput.KEY_G, uinput.KEY_H, uinput.KEY_I, uinput.KEY_J,
    uinput.KEY_K, uinput.KEY_L, uinput.KEY_M, uinput.KEY_N, uinput.KEY_O,
    uinput.KEY_P, uinput.KEY_Q, uinput.KEY_R, uinput.KEY_S, uinput.KEY_T,
    uinput.KEY_U, uinput.KEY_V, uinput.KEY_W, uinput.KEY_X, uinput.KEY_Y,
    uinput.KEY_Z, uinput.KEY_ESC, uinput.KEY_F20, uinput.KEY_F21, uinput.KEY_F22,
    uinput.KEY_F23, uinput.KEY_F24,

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
    left_click()
    time.sleep(0.05)
    mouse.write(e.EV_REL, e.REL_Y, -10)
    mouse.syn()
    time.sleep(0.05)
    left_click()
    time.sleep(0.1)

def upgrade_top(amount = 1):
    for i in range(amount):
        keyboard.emit_click(uinput.KEY_COMMA)
        time.sleep(0.05)

def upgrade_middle(amount = 1):
    for i in range(amount):
        keyboard.emit_click(uinput.KEY_DOT)
        time.sleep(0.05)

def upgrade_bottom(amount = 1):
    for i in range(amount):
        keyboard.emit_click(uinput.KEY_SLASH)
        time.sleep(0.05)

def upgrade_tower():
    # for i in range(0):
    #     keyboard.emit_click(uinput.KEY_DOT)
    #     time.sleep(0.05)
    for i in range(3):
        keyboard.emit_click(uinput.KEY_SLASH)
        time.sleep(0.05)
    keyboard.emit_click(uinput.KEY_ESC)
    time.sleep(0.05)
    keyboard.emit_click(uinput.KEY_C)
    time.sleep(0.05)

async def listen_for_keypress(path, keys):
    dev = InputDevice(path)
    print(f"Listening on {dev.name} ({path})")

    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            if key_event.keycode in keys and key_event.keystate == 0:
                event_queue.put((dev.name, key_event.keycode))

class Overlay(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        # self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        # self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Tool
        )
        self.setStyleSheet("background-color: #788178;")

        self.label = QtWidgets.QLabel("Mode: 1", self)
        self.label.setStyleSheet("color: white; font-size: 12px; padding: 4px;")
        self.label.move(50, 50)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)  # Very small margins
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.adjustSize()

        # self.resize(200, 100)
        self.move(0, 0)

    # def paintEvent(self, event):
    #     painter = QtGui.QPainter(self)
    #     painter.setOpacity(0.1)
    #     painter.setBrush(QtCore.Qt.white)
    #     painter.setPen(QtGui.QPen(QtCore.Qt.white))
    #     painter.drawRect(self.rect())
    #     super().paintEvent(event)

    def update_mode(self, mode_num: int):
        self.label.setText(f"Mode: {mode_num}")

async def main():
    tasks = [asyncio.create_task(listen_for_keypress(tpl[0], tpl[1])) for tpl in device_paths]

    await asyncio.gather(*tasks)

def start_async():
    asyncio.run(main())

def qt5():
    global app, overlay
    app = QtWidgets.QApplication([])
    overlay = Overlay()
    overlay.show()

    def update_loop():
        mode = 1
        while True:
            time.sleep(2)
            mode = (mode % 3) + 1
            # QtCore.QMetaObject.invokeMethod(overlay, "update_mode", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(int, mode))

    Thread(target=update_loop, daemon=True).start()
    app.exec()


def command_processor():
    while True:
        try:
            device_name, key_event = event_queue.get(timeout=1)
            print(f"Processing event from {device_name}: {key_event}")

            if key_event == "KEY_F24":
                global app, overlay
                app.quit()
                sys.exit(0)
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error processing queue item: {e}")

if __name__ == "__main__":
    global app, overlay
    try:
        Thread(target=command_processor, daemon=True).start()
        Thread(target=start_async, daemon=True).start()
        qt5()
    except KeyboardInterrupt:
        print("Goodbye!")
    app.quit()
    sys.exit(0)
    # sys.exit(app.exec_())
