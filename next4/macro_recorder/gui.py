# gui.py
import customtkinter as ctk
from recorder import recording, actions
import json

def start():
    global recording
    recording = True

def stop():
    global recording
    recording = False

def save():
    with open("macros.json", "w") as f:
        json.dump(actions, f, indent=4)

def play():
    import player

app = ctk.CTk()
app.geometry("300x200")

ctk.CTkButton(app, text="Gravar", command=start).pack(pady=10)
ctk.CTkButton(app, text="Parar", command=stop).pack(pady=10)
ctk.CTkButton(app, text="Salvar", command=save).pack(pady=10)
ctk.CTkButton(app, text="Executar", command=play).pack(pady=10)

app.mainloop()
