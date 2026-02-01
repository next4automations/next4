# player.py
import pyautogui
import time
import json

with open("macros.json") as f:
    actions = json.load(f)

for act in actions:
    time.sleep(act["delay"])

    if act["type"] == "click":
        pyautogui.click(act["x"], act["y"])

    elif act["type"] == "key_press":
        pyautogui.press(act["key"].replace("'", ""))
