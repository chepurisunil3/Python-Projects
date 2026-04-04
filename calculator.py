from typing import Literal
from tkinter import END, RIGHT, Button, Entry, StringVar, Tk


root = Tk()
root.title("Calculator")
root.geometry("420x600")
root.minsize(320, 450)
root.configure(bg="#1f2933")

display_value = StringVar(value="0")
just_evaluated = False


def set_display(value: str) -> None:
    display.config(state="normal")
    display.delete(0, END)
    display.insert(0, value)
    display.config(state="readonly")
    display_value.set(value)


def get_display() -> str:
    return display.get()


def append_value(value: str) -> None:
    global just_evaluated

    current = get_display()

    if just_evaluated and value not in {"+", "-", "*", "/"}:
        if value == ".":
            set_display("0.")
        elif value == "(":
            set_display("(")
        else:
            set_display(value)
        just_evaluated = False
        return

    if current in {"0", "Error"} and value not in {".", "+", "-", "*", "/"}:
        set_display(value)
        just_evaluated = False
        return

    if value == ".":
        if current in {"0", "Error"} or current[-1] in "+-*/(":
            set_display("0." if current in {"0", "Error"} else current + "0.")
            just_evaluated = False
            return

        split_index = max(current.rfind(char) for char in "+-*/()")
        current_number = current[split_index + 1:]
        if "." in current_number:
            return

    if value in {"+", "-", "*", "/"}:
        if current == "Error":
            set_display("0")
            just_evaluated = False
            return
        if current[-1] == "(":
            if value != "-":
                return
        elif current[-1] in "+-*/":
            set_display(current[:-1] + value)
            just_evaluated = False
            return

    set_display(current + value)
    just_evaluated = False


def clear_display() -> None:
    global just_evaluated

    set_display("0")
    just_evaluated = False


def backspace() -> None:
    global just_evaluated

    current = get_display()
    if current in {"0", "Error"} or len(current) == 1:
        set_display("0")
        just_evaluated = False
        return
    set_display(current[:-1])
    just_evaluated = False


def calculate() -> None:
    global just_evaluated

    expression = get_display()
    allowed_chars = set("0123456789+-*/.() ")

    if any(char not in allowed_chars for char in expression):
        set_display("Error")
        just_evaluated = False
        return

    try:
        result = eval(expression, {"__builtins__": {}}, {})
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        set_display(str(result))
        just_evaluated = True
    except Exception:
        set_display("Error")
        just_evaluated = False


def handle_keypress(event) -> Literal["break"] | None:
    key = event.keysym
    char = event.char

    if char in "0123456789":
        append_value(char)
        return "break"
    elif char in "+-*/().":
        append_value(char)
        return "break"
    elif key in {"KP_0", "KP_1", "KP_2", "KP_3", "KP_4", "KP_5", "KP_6", "KP_7", "KP_8", "KP_9"}:
        append_value(key[-1])
        return "break"
    elif key in {"KP_Add", "KP_Subtract", "KP_Multiply", "KP_Divide", "parenleft", "parenright"}:
        keypad_map = {
            "KP_Add": "+",
            "KP_Subtract": "-",
            "KP_Multiply": "*",
            "KP_Divide": "/",
            "parenleft": "(",
            "parenright": ")",
        }
        append_value(keypad_map[key])
        return "break"
    elif key in {"KP_Decimal", "decimalpoint"}:
        append_value(".")
        return "break"
    elif key in {"Return", "KP_Enter", "equal"}:
        calculate()
        return "break"
    elif key in {"BackSpace", "Delete"}:
        backspace() if key == "BackSpace" else clear_display()
        return "break"
    elif key == "Escape":
        clear_display()
        return "break"

    return None


def update_font_sizes(event) -> None:
    width = max(event.width, 320)
    height = max(event.height, 450)

    display_font_size = max(18, min(width // 12, height // 14))
    button_font_size = max(14, min(width // 18, height // 24))

    display.config(font=("Segoe UI", display_font_size))

    for button in buttons:
        button.config(font=("Segoe UI", button_font_size, "bold"))


display = Entry(
    root,
    textvariable=display_value,
    justify=RIGHT,
    bd=0,
    relief="flat",
    bg="#e5e7eb",
    fg="#111827",
    insertbackground="#111827",
    state="readonly",
    readonlybackground="#e5e7eb",
)
display.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=12, pady=(12, 8), ipady=18)

button_layout = [
    [("C", clear_display, "#ef4444"), ("⌫", backspace, "#f59e0b"), ("(", lambda: append_value("("), "#374151"), (")", lambda: append_value(")"), "#374151")],
    [("7", lambda: append_value("7"), "#4b5563"), ("8", lambda: append_value("8"), "#4b5563"), ("9", lambda: append_value("9"), "#4b5563"), ("/", lambda: append_value("/"), "#2563eb")],
    [("4", lambda: append_value("4"), "#4b5563"), ("5", lambda: append_value("5"), "#4b5563"), ("6", lambda: append_value("6"), "#4b5563"), ("*", lambda: append_value("*"), "#2563eb")],
    [("1", lambda: append_value("1"), "#4b5563"), ("2", lambda: append_value("2"), "#4b5563"), ("3", lambda: append_value("3"), "#4b5563"), ("-", lambda: append_value("-"), "#2563eb")],
    [("0", lambda: append_value("0"), "#4b5563"), (".", lambda: append_value("."), "#4b5563"), ("=", calculate, "#10b981"), ("+", lambda: append_value("+"), "#2563eb")],
]

buttons = []
for row_index, row in enumerate(button_layout, start=1):
    for column_index, (label, command, color) in enumerate(row):
        button = Button(
            root,
            text=label,
            command=command,
            bd=0,
            relief="flat",
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            cursor="hand2",
        )
        button.grid(
            row=row_index,
            column=column_index,
            sticky="nsew",
            padx=6,
            pady=6,
            ipadx=6,
            ipady=12,
        )
        buttons.append(button)

for row_index in range(6):
    root.grid_rowconfigure(row_index, weight=1)

for column_index in range(4):
    root.grid_columnconfigure(column_index, weight=1)

root.bind_all("<Key>", handle_keypress)
root.bind("<Configure>", update_font_sizes)
display.focus_set()
set_display("0")
root.mainloop()