import time
import json
import threading
import os
import pyautogui
from pynput import mouse, keyboard
import customtkinter as ctk
from tkinter import filedialog

# ===============================
# CONFIG
# ===============================
ctk.set_appearance_mode("dark")
APP_VERSION = "1.1.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# ===============================
# CONFIG DE PASTA (persistente)
# ===============================
def save_config(path):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"macro_path": path}, f)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("macro_path")

MACRO_DIR = load_config() or os.path.join(BASE_DIR, "macros")
os.makedirs(MACRO_DIR, exist_ok=True)

# ===============================
# ESTADO
# ===============================
actions = []
recording = False
mouse_listener = None
keyboard_listener = None
last_time = 0
has_recorded = False
overlay = None

# ===============================
# UTIL
# ===============================
def list_macros():
    return [f.replace(".json", "") for f in os.listdir(MACRO_DIR) if f.endswith(".json")]

def refresh_macros():
    macro_select.configure(values=list_macros())
    if list_macros():
        macro_select.set(list_macros()[0])

def is_mouse_over_overlay(x, y):
    if not overlay:
        return False
    ox = overlay.winfo_rootx()
    oy = overlay.winfo_rooty()
    ow = overlay.winfo_width()
    oh = overlay.winfo_height()
    return ox <= x <= ox + ow and oy <= y <= oy + oh

# ===============================
# CALLBACKS (IGNORAM AÇÕES DO APP)
# ===============================
def on_click(x, y, button, pressed):
    global last_time
    if not recording or not pressed:
        return
    if is_mouse_over_overlay(x, y):
        return

    delay = time.time() - last_time
    actions.append({
        "type": "click",
        "x": x,
        "y": y,
        "delay": delay
    })
    last_time = time.time()

def on_press(key):
    global last_time
    if not recording:
        return

    try:
        if overlay and overlay.focus_get():
            return
    except:
        pass

    delay = time.time() - last_time
    try:
        k = key.char
    except:
        k = str(key).replace("Key.", "")

    actions.append({
        "type": "key",
        "key": k,
        "delay": delay
    })
    last_time = time.time()

def on_scroll(x, y, dx, dy):
    global last_time
    if not recording:
        return
    if is_mouse_over_overlay(x, y):
        return

    delay = time.time() - last_time
    actions.append({
        "type": "scroll",
        "dx": dx,
        "dy": dy,
        "delay": delay
    })
    last_time = time.time()

# ===============================
# OVERLAY
# ===============================
def show_overlay():
    global overlay
    overlay = ctk.CTkToplevel()

    overlay.attributes("-topmost", True)
    overlay.resizable(False, False)

    frame = ctk.CTkFrame(overlay, corner_radius=15)
    frame.pack(expand=True, fill="both", padx=10, pady=10)

    ctk.CTkLabel(frame, text="🔴 Gravando", font=("Arial", 14, "bold")).pack(pady=(5, 8))

    ctk.CTkButton(frame, text="⏹️ Parar", command=stop_record, height=28).pack(fill="x", pady=3)
    ctk.CTkButton(frame, text="💾 Salvar", command=save_macro, height=28).pack(fill="x", pady=3)

    overlay.update_idletasks()

    w = overlay.winfo_width()
    h = overlay.winfo_height()
    x = overlay.winfo_screenwidth() - w - 20
    y = 20

    overlay.geometry(f"{w}x{h}+{x}+{y}")
    overlay.overrideredirect(True)

# ===============================
# CONTROLES
# ===============================
def start_record():
    global recording, actions, last_time, mouse_listener, keyboard_listener, has_recorded

    app.withdraw()
    show_overlay()

    actions.clear()
    has_recorded = True
    recording = True
    last_time = time.time()

    mouse_listener = mouse.Listener(
    on_click=on_click,
    on_scroll=on_scroll)

    keyboard_listener = keyboard.Listener(on_press=on_press)
    mouse_listener.start()
    keyboard_listener.start()

def stop_record():
    global recording, mouse_listener, keyboard_listener, overlay
    recording = False

    if mouse_listener:
        mouse_listener.stop()
    if keyboard_listener:
        keyboard_listener.stop()

    if overlay:
        overlay.destroy()
        overlay = None

    app.deiconify()
    status.configure(text="⏹️ Gravação parada")

def save_macro():
    if not has_recorded:
        status.configure(text="⚠️ Nada para salvar")
        return

    name = macro_name.get().strip()
    if not name:
        status.configure(text="⚠️ Dê um nome à macro")
        return

    path = os.path.join(MACRO_DIR, f"{name}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(actions, f, indent=4)

    refresh_macros()
    status.configure(text=f"💾 Macro '{name}' salva")

def play_macro():
    def run():
        selected = macro_select.get()
        if not selected:
            app.after(0, lambda: status.configure(text="⚠️ Selecione uma macro"))
            return

        path = os.path.join(MACRO_DIR, f"{selected}.json")
        if not os.path.exists(path):
            app.after(0, lambda: status.configure(text="❌ Macro não existe"))
            return

        with open(path, encoding="utf-8") as f:
            acts = json.load(f)

        for a in acts:
            time.sleep(max(a["delay"], 0.05))

            if a["type"] == "click":
                pyautogui.click(a["x"], a["y"])

            elif a["type"] == "scroll":
                pyautogui.scroll(a["dy"] * 100)

            elif a["type"] == "key":
                key = a["key"].lower()

                if key == "cmd":
                    pyautogui.hotkey("ctrl", "esc")
                elif key == "enter":
                    pyautogui.press("enter")
                elif key == "tab":
                    pyautogui.press("tab")
                elif key in ["alt_l", "alt_r"]:
                    pyautogui.keyDown("alt")
                elif key in ["ctrl_l", "ctrl_r"]:
                    pyautogui.keyDown("ctrl")
                elif key in ["shift", "shift_l", "shift_r"]:
                    pyautogui.keyDown("shift")
                elif len(key) == 1:
                    pyautogui.write(key)

        pyautogui.keyUp("alt")
        pyautogui.keyUp("ctrl")
        pyautogui.keyUp("shift")

        app.after(0, lambda: status.configure(text="✅ Executado"))

    threading.Thread(target=run, daemon=True).start()

# ===============================
# ESCOLHER PASTA
# ===============================
def choose_macro_folder():
    global MACRO_DIR
    path = filedialog.askdirectory(title="Escolha a pasta dos macros")
    if not path:
        return

    MACRO_DIR = path
    os.makedirs(MACRO_DIR, exist_ok=True)
    save_config(path)
    refresh_macros()
    status.configure(text=f"📂 Pasta selecionada")

# ===============================
# GUI PRINCIPAL
# ===============================
app = ctk.CTk()
app.geometry("420x420")
app.title("neXt4")

status = ctk.CTkLabel(app, text="Pronto")
status.pack(pady=10)

macro_name = ctk.CTkEntry(app, placeholder_text="Nome da macro")
macro_name.pack(pady=5, fill="x", padx=40)

ctk.CTkButton(app, text="🔴 Gravar", command=start_record).pack(pady=6)
ctk.CTkButton(app, text="💾 Salvar macro", command=save_macro).pack(pady=6)

ctk.CTkButton(app, text="📂 Escolher pasta dos macros", command=choose_macro_folder).pack(pady=6)

macro_select = ctk.CTkComboBox(app, values=list_macros())
macro_select.pack(pady=10, fill="x", padx=40)

ctk.CTkButton(app, text="▶ Executar macro selecionada", command=play_macro).pack(pady=10)

refresh_macros()
app.mainloop()
