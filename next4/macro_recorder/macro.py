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


KEY_MAP = {
    "win": "winleft",
    "ctrl_l": "ctrl",
    "ctrl_r": "ctrl",
    "alt_l": "alt",
    "alt_r": "alt",
    "shift": "shift",
    "shift_l": "shift",
    "shift_r": "shift",
    "enter": "enter",
    "tab": "tab",
    "esc": "esc",
    "space": "space",
    "backspace": "backspace",
    "delete": "delete",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "caps_lock": "capslock",
    "f1": "f1",
    "f2": "f2",
    "f3": "f3",
    "f4": "f4",
    "f5": "f5",
    "f6": "f6",
    "f7": "f7",
    "f8": "f8",
    "f9": "f9",
    "f10": "f10",
    "f11": "f11",
    "f12": "f12"
}
DEFAULT_HOTKEYS = {
    "record": "f8",
    "play": "f9",
    "abort": "esc"
}

def load_hotkeys():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_HOTKEYS.copy()

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("hotkeys", DEFAULT_HOTKEYS.copy())


def save_hotkeys(hotkeys):
    data = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    data["hotkeys"] = hotkeys

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
HOTKEYS = load_hotkeys()


# ===============================
# CONFIG DE PASTA (persistente)
# ===============================
def save_config(path):
    data = {}

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    data["macro_path"] = path

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("macro_path")

MACRO_DIR = load_config() or os.path.join(BASE_DIR, "macros")
os.makedirs(MACRO_DIR, exist_ok=True)

def on_hotkey(key):
    global playing

    if not hotkeys_enabled:
        return

    try:
        pressed = key.char.lower()
    except:
        pressed = str(key).replace("Key.", "").lower()

    if pressed == HOTKEYS["record"]:
        if recording:
            stop_record()
        else:
            start_record()

    elif pressed == HOTKEYS["play"]:
        if not playing:
            play_macro()

    elif pressed == HOTKEYS["abort"]:
        playing = False
        stop_record()
        status.configure(text="⛔ Abortado")

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
playing = False
hotkeys_enabled = True
active_modifiers = set()
MODIFIERS = {
    "ctrl", "ctrl_l", "ctrl_r",
    "alt", "alt_l", "alt_r",
    "shift", "shift_l", "shift_r",
    "win"
}


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
    if not recording:
        return
    if is_mouse_over_overlay(x, y):
        return

    delay = time.time() - last_time

    btn = "left" if button == mouse.Button.left else "right"

    if pressed:
        actions.append({
            "type": "mouse_down",
            "button": btn,
            "x": x,
            "y": y,
            "delay": delay
        })
    else:
        actions.append({
            "type": "mouse_up",
            "button": btn,
            "x": x,
            "y": y,
            "delay": 0
        })

    last_time = time.time()
    atualizar_lista_acoes()



def on_press(key):
    global last_time
    if not recording:
        return

    delay = time.time() - last_time

    try:
        k = key.char
    except AttributeError:
        if key == keyboard.Key.cmd:
            k = "win"
        else:
            k = str(key).replace("Key.", "")

    actions.append({
        "type": "key_down",
        "key": k,
        "delay": delay
    })

    last_time = time.time()

def atualizar_label_atalhos():
    texto = (
        "⌨️ Atalhos\n"
        f"{HOTKEYS['record']}  Gravar / Parar\n"
        f"{HOTKEYS['play']}  Executar\n"
        f"{HOTKEYS['abort']} Abortar"
    )
    shortcuts.configure(text=texto)

def mudar_atalho(acao, nova_tecla):
    HOTKEYS[acao] = nova_tecla.upper()
    atualizar_label_atalhos()

def on_abort(key):
    global playing, last_time
    if key == keyboard.Key.esc:
        playing = False
        return False


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

def on_move(x, y):
    global last_time
    if not recording:
        return
    if is_mouse_over_overlay(x, y):
        return

    delay = time.time() - last_time
    actions.append({
        "type": "mouse_move",
        "x": x,
        "y": y,
        "delay": delay
    })
    last_time = time.time()    
def on_release(key):
    global last_time
    if not recording:
        return

    try:
        k = key.char
    except AttributeError:
        if key == keyboard.Key.cmd:
            k = "win"
        else:
            k = str(key).replace("Key.", "")

    actions.append({
        "type": "key_up",
        "key": k,
        "delay": 0
    })
 

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

    # ... código anterior do frame ...

    ctk.CTkLabel(frame, text="🔴 Gravando", font=("Arial", 14, "bold")).pack(pady=(5, 8))

    # AQUI MUDOU: Adicionei **ESTILO_BOTAO e ajustei a altura
    ctk.CTkButton(frame, text="⏹️ Parar", command=stop_record, height=32, **ESTILO_BOTAO).pack(fill="x", pady=3)
    ctk.CTkButton(frame, text="💾 Salvar", command=save_macro, height=32, **ESTILO_BOTAO).pack(fill="x", pady=3)

    overlay.update_idletasks()
    # ... resto do código ...

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
    on_scroll=on_scroll
)



    keyboard_listener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release
    )

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
        overlay.after(0, overlay.destroy)
        overlay = None


    app.deiconify()
    status.configure(text="⏹️ Gravação parada")

def atualizar_lista_acoes():
    # Limpa tudo do frame
    for widget in actions_box.winfo_children():
        widget.destroy()

    for idx, a in enumerate(actions):
        frame = ctk.CTkFrame(actions_box, corner_radius=8, fg_color="#2a2a2a")
        frame.pack(fill="x", pady=2, padx=2)

        # Label com a ação
        label = ctk.CTkLabel(frame, text=formatar_acao(a, idx), anchor="w")
        label.pack(side="left", padx=(6, 0), expand=True, fill="x")

        # Botão editar delay
        btn_edit = ctk.CTkButton(
            frame,
            text="✏️",
            width=30,
            command=lambda i=idx: editar_delay_selecionado(i)
        )
        btn_edit.pack(side="left", padx=4)

        # Botão remover ação
        btn_remove = ctk.CTkButton(
            frame,
            text="🗑",
            width=30,
            fg_color="#a83232",
            hover_color="#8f2a2a",
            command=lambda i=idx: remover_acao_por_indice(i)
        )
        btn_remove.pack(side="left", padx=4)

        # Botão adicionar ação
        btn_add = ctk.CTkButton(
            frame,
            text="➕",
            width=30,
            command=lambda i=idx: adicionar_acao_apos(i)
        )
        btn_add.pack(side="left", padx=4)
def editar_delay_selecionado(index):
    a = actions[index]
    win = ctk.CTkToplevel(app)
    win.title("Editar Delay")
    win.geometry("220x120")
    win.grab_set()

    ctk.CTkLabel(win, text="Delay (segundos):").pack(pady=6)
    entry = ctk.CTkEntry(win)
    entry.insert(0, str(a.get("delay", 0)))
    entry.pack(pady=4)

    def salvar():
        try:
            actions[index]["delay"] = float(entry.get())
            atualizar_lista_acoes()
            win.destroy()
        except:
            status.configure(text="❌ Valor inválido")

    ctk.CTkButton(win, text="Salvar", command=salvar).pack(pady=8)


def remover_acao_por_indice(index):
    if 0 <= index < len(actions):
        actions.pop(index)
        atualizar_lista_acoes()


def adicionar_acao_apos(index):
    # Cria ação vazia de exemplo
    nova = {"type": "key_down", "key": "a", "delay": 0.5}
    actions.insert(index + 1, nova)
    atualizar_lista_acoes()


def editar_delay(event):
    index = int(actions_box.index(f"@{event.x},{event.y}").split(".")[0]) - 1
    if index < 0 or index >= len(actions):
        return

    win = ctk.CTkToplevel(app)
    win.title("Editar Delay")
    win.geometry("220x120")
    win.grab_set()

    ctk.CTkLabel(win, text="Delay (segundos):").pack(pady=6)
    entry = ctk.CTkEntry(win)
    entry.insert(0, str(actions[index]["delay"]))
    entry.pack(pady=4)
    def salvar():
        try:
            actions[index]["delay"] = float(entry.get())
            atualizar_lista_acoes()
            win.destroy()
        except:
            pass

    ctk.CTkButton(win, text="Salvar", command=salvar).pack(pady=8)
def editar_delay_selecionado_acao(idx=None):
    if idx is None:
        # Se não passou índice, tenta pegar o selecionado
        idx = editar_delay_selecionado_acao()
    if idx is None or idx >= len(actions):
        status.configure(text="⚠️ Selecione uma ação")
        return

    win = ctk.CTkToplevel(app)
    win.title("Editar Delay")
    win.geometry("220x120")
    win.grab_set()

    ctk.CTkLabel(win, text="Delay (segundos):").pack(pady=6)
    entry = ctk.CTkEntry(win)
    entry.insert(0, str(actions[idx].get("delay", 0)))
    entry.pack(pady=4)

    def salvar():
        try:
            actions[idx]["delay"] = float(entry.get())
            atualizar_lista_acoes()
            win.destroy()
        except:
            status.configure(text="❌ Valor inválido")

    ctk.CTkButton(win, text="Salvar", command=salvar).pack(pady=8)

def remover_acao_selecionada():
    idx = editar_delay_selecionado_acao()
    if idx is None or idx >= len(actions):
        status.configure(text="⚠️ Selecione uma ação")
        return

    actions.pop(idx)
    atualizar_lista_acoes()
    status.configure(text="🗑 Ação removida")

def remover_acao(event):
    index = int(actions_box.index(f"@{event.x},{event.y}").split(".")[0]) - 1
    if 0 <= index < len(actions):
        del actions[index]
        atualizar_lista_acoes()


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
    

def formatar_acao(a, idx):
    delay = f"⏱ {round(a.get('delay', 0), 2)}s"

    if a["type"] == "mouse_down":
        return f"{idx}. 🖱 Segurar {a['button']}  {delay}"

    if a["type"] == "mouse_up":
        return f"{idx}. 🖱 Soltar {a['button']}"

    if a["type"] == "click":
        return f"{idx}. 🖱 Clique  {delay}"

    if a["type"] == "scroll":
        return f"{idx}. 🧻 Scroll  {delay}"

    if a["type"] == "key_down":
        return f"{idx}. ⌨️ {a['key'].upper()} ↓  {delay}"
    
    if a["type"] == "mouse_move":
        return f"{idx}. 🖱 Mover mouse para ({a['x']},{a['y']}) ⏱ {round(a.get('delay', 0), 2)}s"

    if a["type"] == "key_up":
        return f"{idx}. ⌨️ {a['key'].upper()} ↑"

    return None


play_overlay = None
play_overlay_label = None

def show_play_overlay(text):
    global play_overlay, play_overlay_label

    if not play_overlay:
        play_overlay = ctk.CTkToplevel()
        play_overlay.attributes("-topmost", True)
        play_overlay.overrideredirect(True)

        frame = ctk.CTkFrame(play_overlay, corner_radius=12)
        frame.pack(expand=True, fill="both", padx=8, pady=8)

        play_overlay_label = ctk.CTkLabel(
            frame,
            text="",
            font=("Arial", 14, "bold")
        )
        play_overlay_label.pack(padx=10, pady=6)

        play_overlay.update_idletasks()
        w, h = 260, 50
        x = play_overlay.winfo_screenwidth() // 2 - w // 2
        y = 40
        play_overlay.geometry(f"{w}x{h}+{x}+{y}")

    play_overlay_label.configure(text=text)
def hide_play_overlay():
    global play_overlay
    if play_overlay:
        play_overlay.destroy()
        play_overlay = None

def play_macro():
    def run():
        global playing, active_modifiers
        playing = True
        active_modifiers.clear()

        abort_listener = keyboard.Listener(on_press=on_abort)
        abort_listener.start()

        selected = macro_select.get()
        if not selected:
            app.after(0, lambda: status.configure(text="⚠️ Selecione uma macro"))
            playing = False
            return

        path = os.path.join(MACRO_DIR, f"{selected}.json")
        if not os.path.exists(path):
            app.after(0, lambda: status.configure(text="❌ Macro não existe"))
            playing = False
            return

        with open(path, encoding="utf-8") as f:
            acts = json.load(f)

        for a in acts:
            if not playing:
                break

            time.sleep(max(a.get("delay", 0), 0.005))

            # ===============================
            # MOUSE CLICK
            # ===============================
            if a["type"] == "click":
                show_play_overlay("🖱 Clique do mouse")
                pyautogui.click(a["x"], a["y"])

            # ===============================
            # SCROLL
            # ===============================
            elif a["type"] == "scroll":
                direcao = "⬆️ Scroll" if a["dy"] > 0 else "⬇️ Scroll"
                show_play_overlay(direcao)
                pyautogui.scroll(a["dy"] * 100)

            # ===============================
            # KEY DOWN
            # ===============================
            elif a["type"] == "key_down":
                key = a["key"].lower()
                mapped = KEY_MAP.get(key, key)

                show_play_overlay(f"⌨️ {key.upper()} pressionada")

                if key in MODIFIERS:
                    active_modifiers.add(key)
                    pyautogui.keyDown(mapped)
                else:
                    if active_modifiers:
                        pyautogui.keyDown(mapped)
                    else:
                        pyautogui.press(mapped)

            # ===============================
            # KEY UP
            # ===============================
            elif a["type"] == "key_up":
                key = a["key"].lower()
                mapped = KEY_MAP.get(key, key)

                show_play_overlay(f"⌨️ {key.upper()} solta")

                pyautogui.keyUp(mapped)
                active_modifiers.discard(key)
            elif a["type"] == "mouse_down":
                show_play_overlay(f"🖱 Segurar {a['button']}")
                pyautogui.mouseDown(a["x"], a["y"], button=a["button"])
            elif a["type"] == "mouse_up":
                show_play_overlay(f"🖱 Soltar {a['button']}")
                pyautogui.mouseUp(a["x"], a["y"], button=a["button"])



        # ===============================
        # FINALIZAÇÃO
        # ===============================
        playing = False
        abort_listener.stop()
        hide_play_overlay()

        # garante limpeza total
        for k in ["alt", "ctrl", "shift", "winleft"]:
            pyautogui.keyUp(k)

        app.after(0, lambda: status.configure(text="✅ Macro finalizada"))

    threading.Thread(target=run, daemon=True).start()
def simplificar_acoes(acoes):
    novas = []
    i = 0

    while i < len(acoes) - 1:
        atual = acoes[i]
        prox = acoes[i + 1]

        if atual["type"] == "mouse_down" and prox["type"] == "mouse_up":
            novas.append({
                "type": "click",
                "x": atual["x"],
                "y": atual["y"],
                "button": atual["button"]
            })
            i += 2
        else:
            i += 1

    return novas

def delete_macro():
    selected = macro_select.get()
    if not selected:
        status.configure(text="⚠️ Nenhuma macro selecionada")
        return

    path = os.path.join(MACRO_DIR, f"{selected}.json")
    if not os.path.exists(path):
        status.configure(text="❌ Macro não encontrada")
        return

    os.remove(path)
    refresh_macros()
    status.configure(text=f"🗑 Macro '{selected}' excluída")
def get_acao_selecionada():
    try:
        index = actions_box.index("insert")
        linha = int(index.split(".")[0]) - 1
        return linha
    except:
        return None

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
# --- CONFIGURAÇÃO DE ESTILO DOS BOTÕES (LILÁS) ---
ESTILO_BOTAO = {
    "corner_radius": 20,
    "fg_color": "#9B59B6",      # Lilás
    "hover_color": "#8E44AD",   # Lilás escuro
    "font": ("Roboto", 14, "bold"),
    "text_color": "white",
    "border_width": 1,
    "border_color": "white"
}
# -------------------------------------------------

app = ctk.CTk() # Essa linha já existe no seu código
# ===============================
# GUI PRINCIPAL
# ===============================
def open_settings():
    win = ctk.CTkToplevel(app)
    win.title("Configurações")
    win.geometry("320x300")
    win.resizable(False, False)
    win.grab_set()

    ctk.CTkLabel(win, text="⌨️ Atalhos do Programa", font=("Arial", 14, "bold")).pack(pady=10)

    entries = {}

    def add_field(label, key):
        frame = ctk.CTkFrame(win, fg_color="transparent")
        frame.pack(pady=6, padx=20, fill="x")

        ctk.CTkLabel(frame, text=label, width=120, anchor="w").pack(side="left")
        e = ctk.CTkEntry(frame, width=100)
        e.insert(0, HOTKEYS[key])
        e.pack(side="right")
        entries[key] = e

    add_field("Gravar / Parar", "record")
    add_field("Executar macro", "play")
    add_field("Abortar", "abort")

    def save():
        for k, e in entries.items():
            HOTKEYS[k] = e.get().lower()

        save_hotkeys(HOTKEYS)

        atualizar_label_atalhos()  # 👈 AQUI ESTÁ A CHAVE

        status.configure(text="⚙️ Atalhos atualizados")
        win.destroy()


    ctk.CTkButton(win, text="💾 Salvar", command=save).pack(pady=15)

app = ctk.CTk()
app.geometry("400x600")
app.title("neXt4")

status = ctk.CTkLabel(app, text="Pronto")
status.pack(pady=8)

# ==============================
# BLOCO DE GRAVAÇÃO
# ===============================
# ===============================
# BLOCO DE GRAVAÇÃO
# ===============================
macro_name = ctk.CTkEntry(app, placeholder_text="Nome da macro")
macro_name.pack(pady=6, fill="x", padx=40)

record_frame = ctk.CTkFrame(app, fg_color="transparent")
record_frame.pack(pady=4)

# Botões Gravar e Salvar
ctk.CTkButton(record_frame, text="🔴 Gravar", command=start_record, width=120, **ESTILO_BOTAO).pack(side="left", padx=6)
ctk.CTkButton(record_frame, text="💾 Salvar", command=save_macro, width=120, **ESTILO_BOTAO).pack(side="left", padx=6)

ctk.CTkLabel(app, text="🧠 Ações da Macro", font=("Arial", 14, "bold")).pack(pady=(12, 4))

actions_box = ctk.CTkTextbox(app, width=360, height=160)
actions_box.bind("<Double-Button-1>", editar_delay)
actions_box.bind("<Button-3>", remover_acao)
actions_box.pack(pady=6)
actions_box.configure(state="disabled")

actions_buttons = ctk.CTkFrame(app)
actions_buttons.pack(pady=4)

# Botões Editar e Remover Ação
ctk.CTkButton(
    actions_buttons,
    text="✏️ Editar delay",
    width=160,
    command=lambda: editar_delay_selecionado(),
    **ESTILO_BOTAO
).pack(side="left", padx=6)

ctk.CTkButton(
    actions_buttons,
    text="🗑 Remover ação",
    width=160,
    command=lambda: remover_acao_selecionada(),
    **ESTILO_BOTAO # Nota: Se quiser manter vermelho, remova esta linha e use fg_color="#a83232"
).pack(side="left", padx=6)

# ===============================
# BLOCO DE MACROS
# ===============================
ctk.CTkLabel(app, text="Macros", font=("Arial", 13, "bold")).pack(pady=(12, 4))

macro_select = ctk.CTkComboBox(app, values=list_macros())
macro_select.pack(pady=4, fill="x", padx=40)

macro_action_frame = ctk.CTkFrame(app, fg_color="transparent")
macro_action_frame.pack(pady=6)

# Botões Executar e Excluir Macro
ctk.CTkButton(
    macro_action_frame,
    text="▶ Executar",
    command=play_macro,
    width=120,
    **ESTILO_BOTAO
).pack(side="left", padx=6)

ctk.CTkButton(
    macro_action_frame,
    text="🗑 Excluir",
    command=delete_macro,
    width=120,
    **ESTILO_BOTAO
).pack(side="left", padx=6)

# Botão Configurações
ctk.CTkButton(
    app,
    text="⚙️ Configurações",
    command=open_settings,
    **ESTILO_BOTAO
).pack(pady=6)

# ===============================
# CONFIGURAÇÕES
# ===============================
ctk.CTkButton(
    app,
    text="📂 Pasta dos macros",
    command=choose_macro_folder,
    **ESTILO_BOTAO
).pack(pady=10)
# ===============================
# ATALHOS (RESUMIDO)
# ===============================

shortcuts = ctk.CTkLabel(
    app,
    text="",
    justify="left"
)
shortcuts.pack(pady=10)
#S
atualizar_label_atalhos()  # ✅ agora existe

refresh_macros()
keyboard.Listener(on_press=on_hotkey).start()
app.mainloop()
