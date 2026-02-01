# recorder.py
import time
from pynput import mouse, keyboard
import json

actions = []
recording = False
last_time = time.time()

def on_click(x, y, button, pressed):
    global last_time
    if recording and pressed:
        delay = time.time() - last_time
        actions.append({
            "type": "click",
            "x": x,
            "y": y,
            "button": str(button),
            "delay": delay
        })
        last_time = time.time()

def on_press(key):
    global last_time
    if recording:
        delay = time.time() - last_time
        actions.append({
            "type": "key_press",
            "key": str(key),
            "delay": delay
        })
        last_time = time.time()

mouse_listener = mouse.Listener(on_click=on_click)
keyboard_listener = keyboard.Listener(on_press=on_press)
mouse_listener.start()
keyboard_listener.start()
