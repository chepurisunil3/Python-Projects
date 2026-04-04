from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk


BACKGROUND = "#4934d4"
PANEL = "#f7f8ff"
CARD_BG = "#ffffff"
ACCENT = "#6d63ff"
ACCENT_DARK = "#5247ee"
ACCENT_LIGHT = "#ece9ff"
TEXT = "#171a2b"
MUTED = "#8d92a8"
CANVAS_BG = "#ffffff"
BORDER = "#dfe4f3"
BUTTON_BG = "#f3f5ff"


@dataclass
class PaintState:
    current_tool: str = "pencil"
    outline_color: str = "#111111"
    fill_color: str = ""
    brush_size: int = 3
    current_item: int | None = None
    start_x: int | None = None
    start_y: int | None = None
    polygon_points: list[int] = field(default_factory=list)
    polygon_preview: int | None = None
    history: list[int] = field(default_factory=list)


class PaintApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Paint")
        self.root.minsize(900, 600)
        self.root.geometry("1200x760")
        self.root.configure(bg=BACKGROUND)

        self.state = PaintState()
        self.tool_buttons: dict[str, ttk.Button] = {}

        self.status_var = tk.StringVar(value="Ready")
        self.outline_var = tk.StringVar(value=self.state.outline_color)
        self.fill_var = tk.StringVar(value="transparent")
        self.brush_var = tk.IntVar(value=self.state.brush_size)
        self.outline_preview: tk.Label | None = None
        self.fill_preview: tk.Label | None = None
        self.sidebar_canvas: tk.Canvas | None = None
        self.sidebar_window: int | None = None

        self._configure_styles()
        self._build_layout()
        self._bind_events()
        self._refresh_color_previews()
        self._set_tool("pencil")

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Sidebar.TFrame", background=PANEL)
        style.configure("Main.TFrame", background=CARD_BG)
        style.configure(
            "Tool.TButton",
            background=BUTTON_BG,
            foreground=TEXT,
            padding=10,
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            focusthickness=0,
            relief="flat",
        )
        style.map(
            "Tool.TButton",
            background=[("active", ACCENT_LIGHT), ("pressed", ACCENT_LIGHT)],
            foreground=[("active", ACCENT_DARK), ("pressed", ACCENT_DARK)],
        )
        style.configure(
            "ActiveTool.TButton",
            background=ACCENT_LIGHT,
            foreground=ACCENT_DARK,
            padding=10,
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            focusthickness=0,
            relief="flat",
        )
        style.map(
            "ActiveTool.TButton",
            background=[("active", ACCENT_LIGHT), ("pressed", ACCENT_LIGHT)],
            foreground=[("active", ACCENT_DARK), ("pressed", ACCENT_DARK)],
        )
        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground=CARD_BG,
            padding=10,
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            focusthickness=0,
            relief="flat",
        )
        style.map(
            "Accent.TButton",
            background=[("active", ACCENT_DARK), ("pressed", ACCENT_DARK)],
            foreground=[("active", CARD_BG), ("pressed", CARD_BG)],
        )
        style.configure("Section.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 11, "bold"))
        style.configure("Info.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("CanvasInfo.TLabel", background=CARD_BG, foreground=MUTED, font=("Segoe UI", 10))

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        shell = tk.Frame(self.root, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        shell.grid(row=0, column=0, sticky="nsew", padx=28, pady=28)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        sidebar_shell = tk.Frame(shell, bg=PANEL, width=250)
        sidebar_shell.grid(row=0, column=0, sticky="ns")
        sidebar_shell.grid_propagate(False)
        sidebar_shell.columnconfigure(0, weight=1)
        sidebar_shell.rowconfigure(1, weight=1)

        sidebar_header = tk.Frame(sidebar_shell, bg=PANEL)
        sidebar_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(18, 8))
        tk.Label(sidebar_header, text="Creative Paint", bg=PANEL, fg=TEXT, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(
            sidebar_header,
            text="A simple drawing workspace with modern tools.",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 0))

        self.sidebar_canvas = tk.Canvas(sidebar_shell, bg=PANEL, highlightthickness=0, bd=0)
        sidebar_scrollbar = ttk.Scrollbar(sidebar_shell, orient="vertical", command=self.sidebar_canvas.yview)
        self.sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)
        self.sidebar_canvas.grid(row=1, column=0, sticky="nsew")
        sidebar_scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 10), padx=(0, 6))

        self.sidebar = ttk.Frame(self.sidebar_canvas, style="Sidebar.TFrame", padding=(14, 6, 12, 14))
        self.sidebar_window = self.sidebar_canvas.create_window((0, 0), window=self.sidebar, anchor="nw")
        self.sidebar.bind("<Configure>", self._on_sidebar_frame_configure)
        self.sidebar_canvas.bind("<Configure>", self._on_sidebar_canvas_configure)
        self.sidebar_canvas.bind("<MouseWheel>", self._on_sidebar_mousewheel)
        self.sidebar.bind("<MouseWheel>", self._on_sidebar_mousewheel)

        self.main = ttk.Frame(shell, style="Main.TFrame", padding=(22, 18, 22, 18))
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(1, weight=1)

        ttk.Label(self.sidebar, text="Tools", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))

        tools = [
            ("pencil", "Pencil"),
            ("line", "Line"),
            ("rectangle", "Rectangle"),
            ("oval", "Oval"),
            ("polygon", "Polygon"),
            ("fill", "Fill"),
        ]

        for index, (tool_name, label) in enumerate(tools, start=1):
            button = ttk.Button(self.sidebar, text=label, style="Tool.TButton", command=lambda name=tool_name: self._set_tool(name))
            button.grid(row=index, column=0, sticky="ew", pady=4)
            self.tool_buttons[tool_name] = button

        ttk.Label(self.sidebar, text="Colors", style="Section.TLabel").grid(row=8, column=0, sticky="w", pady=(18, 8))

        ttk.Button(self.sidebar, text="Outline color", command=self._choose_outline_color).grid(row=9, column=0, sticky="ew", pady=4)
        ttk.Label(self.sidebar, textvariable=self.outline_var, style="Info.TLabel").grid(row=10, column=0, sticky="w")
        self.outline_preview = tk.Label(self.sidebar, bg=self.state.outline_color, relief="solid", bd=1, width=18, height=1)
        self.outline_preview.grid(row=11, column=0, sticky="ew", pady=(4, 6))

        ttk.Button(self.sidebar, text="Fill color", command=self._choose_fill_color).grid(row=12, column=0, sticky="ew", pady=(8, 4))
        ttk.Label(self.sidebar, textvariable=self.fill_var, style="Info.TLabel").grid(row=13, column=0, sticky="w")
        self.fill_preview = tk.Label(self.sidebar, bg=CANVAS_BG, relief="solid", bd=1, width=18, height=1)
        self.fill_preview.grid(row=14, column=0, sticky="ew", pady=(4, 6))

        ttk.Button(self.sidebar, text="Clear fill", command=self._clear_fill_color).grid(row=15, column=0, sticky="ew", pady=(4, 10))

        ttk.Label(self.sidebar, text="Brush size", style="Section.TLabel").grid(row=16, column=0, sticky="w", pady=(8, 8))
        self.size_scale = ttk.Scale(self.sidebar, from_=1, to=18, orient="horizontal", command=self._on_brush_size_change)
        self.size_scale.grid(row=17, column=0, sticky="ew")

        self.size_label = ttk.Label(self.sidebar, text=f"{self.state.brush_size}px", style="Info.TLabel")
        self.size_label.grid(row=18, column=0, sticky="w", pady=(4, 12))
        self.size_scale.set(self.state.brush_size)

        ttk.Label(self.sidebar, text="Actions", style="Section.TLabel").grid(row=19, column=0, sticky="w", pady=(8, 8))
        ttk.Button(self.sidebar, text="Undo", command=self._undo_last).grid(row=20, column=0, sticky="ew", pady=4)
        ttk.Button(self.sidebar, text="Clear canvas", command=self._clear_canvas).grid(row=21, column=0, sticky="ew", pady=4)
        ttk.Button(self.sidebar, text="Save drawing", style="Accent.TButton", command=self._save_canvas).grid(row=22, column=0, sticky="ew", pady=4)

        ttk.Label(
            self.sidebar,
            text="Polygon: left click to add points, right click or Enter to finish.",
            style="Info.TLabel",
            wraplength=180,
            justify="left",
        ).grid(row=23, column=0, sticky="ew", pady=(12, 0))

        toolbar = ttk.Frame(self.main, style="Main.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(0, weight=1)

        tk.Label(toolbar, text="Paint workspace", font=("Segoe UI", 18, "bold"), fg=TEXT, bg=CARD_BG).grid(row=0, column=0, sticky="w")
        tk.Label(toolbar, text="Draw, fill, and save using the tools on the left.", font=("Segoe UI", 10), fg=MUTED, bg=CARD_BG).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(toolbar, textvariable=self.status_var, style="CanvasInfo.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 0))

        canvas_container = tk.Frame(self.main, bg="#edf1ff", highlightthickness=1, highlightbackground=BORDER, bd=0)
        canvas_container.grid(row=1, column=0, sticky="nsew")
        canvas_container.pack_propagate(False)

        self.canvas = tk.Canvas(
            canvas_container,
            bg=CANVAS_BG,
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)

    def _on_sidebar_frame_configure(self, event: tk.Event[tk.Misc] | None = None) -> None:
        if self.sidebar_canvas is not None:
            self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))

    def _on_sidebar_canvas_configure(self, event: tk.Event[tk.Misc]) -> None:
        if self.sidebar_canvas is not None and self.sidebar_window is not None:
            self.sidebar_canvas.itemconfigure(self.sidebar_window, width=event.width)

    def _on_sidebar_mousewheel(self, event: tk.Event[tk.Misc]) -> None:
        if self.sidebar_canvas is None:
            return

        scroll_region = self.sidebar_canvas.bbox("all")
        if scroll_region is None:
            return

        total_height = scroll_region[3] - scroll_region[1]
        if total_height <= self.sidebar_canvas.winfo_height():
            return

        delta = -int(event.delta / 120) if event.delta else 0
        if delta != 0:
            self.sidebar_canvas.yview_scroll(delta, "units")

    def _bind_events(self) -> None:
        self.canvas.bind("<Button-1>", self._on_left_button_down)
        self.canvas.bind("<B1-Motion>", self._on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_button_up)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Motion>", self._on_mouse_move)

        self.root.bind("<Escape>", self._handle_escape)
        self.root.bind("<Return>", self._handle_return)
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Control-s>", lambda event: self._save_canvas())
        self.root.bind("<Control-z>", lambda event: self._undo_last())
        self.root.bind("<Delete>", lambda event: self._clear_canvas())

    def _set_tool(self, tool_name: str) -> None:
        self._cancel_polygon_preview(reset_points=tool_name != "polygon")
        self.state.current_tool = tool_name

        for name, button in self.tool_buttons.items():
            button.configure(style="ActiveTool.TButton" if name == tool_name else "Tool.TButton")

        tool_messages = {
            "pencil": "Draw freehand with the left mouse button.",
            "line": "Click and drag to create a straight line.",
            "rectangle": "Click and drag to draw a rectangle.",
            "oval": "Click and drag to draw an oval.",
            "polygon": "Left click to place polygon points. Right click or Enter to finish.",
            "fill": "Click any supported shape to apply the current fill color.",
        }
        self.status_var.set(tool_messages[tool_name])

    def _choose_outline_color(self) -> None:
        result = colorchooser.askcolor(color=self.state.outline_color, title="Choose outline color", parent=self.root)
        if result[1]:
            self.state.outline_color = result[1]
            self.outline_var.set(self.state.outline_color)
            self._refresh_color_previews()
            self.status_var.set(f"Outline color set to {self.state.outline_color}")

    def _choose_fill_color(self) -> None:
        start_color = self.state.fill_color or "#ffffff"
        result = colorchooser.askcolor(color=start_color, title="Choose fill color", parent=self.root)
        if result[1]:
            self.state.fill_color = result[1]
            self.fill_var.set(self.state.fill_color)
            self._refresh_color_previews()
            self.status_var.set(f"Fill color set to {self.state.fill_color}")

    def _clear_fill_color(self) -> None:
        self.state.fill_color = ""
        self.fill_var.set("transparent")
        self._refresh_color_previews()
        self.status_var.set("Fill color cleared")

    def _refresh_color_previews(self) -> None:
        if self.outline_preview is not None:
            self.outline_preview.configure(bg=self.state.outline_color)

        if self.fill_preview is not None:
            fill_display = self.state.fill_color if self.state.fill_color else CANVAS_BG
            self.fill_preview.configure(bg=fill_display)

    def _on_brush_size_change(self, value: str) -> None:
        size = max(1, round(float(value)))
        self.state.brush_size = size
        self.brush_var.set(size)
        if hasattr(self, "size_label"):
            self.size_label.configure(text=f"{size}px")

    def _normalize_bounds(self, x1: int, y1: int, x2: int, y2: int) -> tuple[int, int, int, int]:
        return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)

    def _shape_fill(self) -> str:
        return self.state.fill_color if self.state.fill_color else ""

    def _item_contains_point(self, item_id: int, x: int, y: int) -> bool:
        item_type = self.canvas.type(item_id)
        x1, y1, x2, y2 = self.canvas.bbox(item_id) or (0, 0, 0, 0)

        if item_type in {"rectangle", "oval", "polygon"}:
            return x1 <= x <= x2 and y1 <= y <= y2

        return False

    def _find_fill_target(self, x: int, y: int) -> int | None:
        overlapping = self.canvas.find_overlapping(x - 1, y - 1, x + 1, y + 1)
        for item_id in reversed(overlapping):
            if self.canvas.type(item_id) in {"rectangle", "oval", "polygon", "line"}:
                if self.canvas.type(item_id) == "line" or self._item_contains_point(item_id, x, y):
                    return item_id

        closest = self.canvas.find_closest(x, y, halo=6)
        if closest:
            item_id = closest[0]
            if self.canvas.type(item_id) in {"rectangle", "oval", "polygon", "line"}:
                return item_id
        return None

    def _register_item(self, item_id: int) -> None:
        self.state.history.append(item_id)

    def _on_left_button_down(self, event: tk.Event[tk.Misc]) -> None:
        tool = self.state.current_tool

        if tool == "fill":
            self._fill_shape(event.x, event.y)
            return

        if tool == "polygon":
            self._add_polygon_point(event.x, event.y)
            return

        self.state.start_x = event.x
        self.state.start_y = event.y

        if tool == "pencil":
            item_id = self.canvas.create_line(
                event.x,
                event.y,
                event.x,
                event.y,
                fill=self.state.outline_color,
                width=self.state.brush_size,
                capstyle=tk.ROUND,
                smooth=True,
                splinesteps=18,
            )
            self.state.current_item = item_id
            self._register_item(item_id)

        elif tool == "line":
            item_id = self.canvas.create_line(
                event.x,
                event.y,
                event.x,
                event.y,
                fill=self.state.outline_color,
                width=self.state.brush_size,
                capstyle=tk.ROUND,
            )
            self.state.current_item = item_id
            self._register_item(item_id)

        elif tool == "rectangle":
            item_id = self.canvas.create_rectangle(
                event.x,
                event.y,
                event.x,
                event.y,
                outline=self.state.outline_color,
                fill=self._shape_fill(),
                width=self.state.brush_size,
            )
            self.state.current_item = item_id
            self._register_item(item_id)

        elif tool == "oval":
            item_id = self.canvas.create_oval(
                event.x,
                event.y,
                event.x,
                event.y,
                outline=self.state.outline_color,
                fill=self._shape_fill(),
                width=self.state.brush_size,
            )
            self.state.current_item = item_id
            self._register_item(item_id)

    def _on_left_drag(self, event: tk.Event[tk.Misc]) -> None:
        tool = self.state.current_tool
        item_id = self.state.current_item

        if tool == "polygon":
            return

        if item_id is None or self.state.start_x is None or self.state.start_y is None:
            return

        if tool == "pencil":
            points = self.canvas.coords(item_id)
            points.extend((event.x, event.y))
            self.canvas.coords(item_id, *points)
        elif tool == "line":
            self.canvas.coords(item_id, self.state.start_x, self.state.start_y, event.x, event.y)
        elif tool in {"rectangle", "oval"}:
            x1, y1, x2, y2 = self._normalize_bounds(self.state.start_x, self.state.start_y, event.x, event.y)
            self.canvas.coords(item_id, x1, y1, x2, y2)

    def _on_left_button_up(self, event: tk.Event[tk.Misc]) -> None:
        tool = self.state.current_tool

        if tool in {"pencil", "line", "rectangle", "oval"}:
            self.state.current_item = None
            self.state.start_x = None
            self.state.start_y = None

    def _fill_shape(self, x: int, y: int) -> None:
        target_color = self.state.fill_color or self.state.outline_color
        if not target_color:
            self.status_var.set("Choose a color first.")
            return

        item_id = self._find_fill_target(x, y)
        if item_id is None:
            self.status_var.set("No shape found at that location.")
            return

        item_type = self.canvas.type(item_id)
        if item_type not in {"rectangle", "oval", "polygon", "line"}:
            self.status_var.set("Color fill works with drawn shapes and strokes.")
            return

        if item_type == "line":
            self.canvas.itemconfigure(item_id, fill=target_color)
            self.status_var.set("Stroke recolored.")
            return

        self.canvas.itemconfigure(item_id, fill=target_color)
        self.status_var.set(f"Filled selected {item_type}.")

    def _add_polygon_point(self, x: int, y: int) -> None:
        self.state.polygon_points.extend((x, y))

        if len(self.state.polygon_points) == 2:
            preview_id = self.canvas.create_line(
                *self.state.polygon_points,
                fill=self.state.outline_color,
                width=self.state.brush_size,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )
            self.state.polygon_preview = preview_id
        else:
            self._update_polygon_preview(x, y)

        point_count = len(self.state.polygon_points) // 2
        self.status_var.set(f"Polygon point {point_count} added. Right click or press Enter to finish.")

    def _update_polygon_preview(self, x: int, y: int) -> None:
        preview_id = self.state.polygon_preview
        if preview_id is None:
            return

        preview_points = [*self.state.polygon_points, x, y]
        self.canvas.coords(preview_id, *preview_points)

    def _on_mouse_move(self, event: tk.Event[tk.Misc]) -> None:
        if self.state.current_tool == "polygon" and self.state.polygon_points and self.state.polygon_preview is not None:
            self._update_polygon_preview(event.x, event.y)

    def _finish_polygon(self) -> None:
        if len(self.state.polygon_points) < 6:
            self.status_var.set("A polygon needs at least 3 points.")
            return

        if self.state.polygon_preview is not None:
            self.canvas.delete(self.state.polygon_preview)
            self.state.polygon_preview = None

        polygon_id = self.canvas.create_polygon(
            *self.state.polygon_points,
            outline=self.state.outline_color,
            fill=self._shape_fill(),
            width=self.state.brush_size,
            joinstyle=tk.ROUND,
        )
        self._register_item(polygon_id)
        self.state.polygon_points.clear()
        self.status_var.set("Polygon created.")

    def _cancel_polygon_preview(self, reset_points: bool = True) -> None:
        if self.state.polygon_preview is not None:
            self.canvas.delete(self.state.polygon_preview)
            self.state.polygon_preview = None

        if reset_points:
            self.state.polygon_points.clear()

    def _on_right_click(self, event: tk.Event[tk.Misc]) -> None:
        if self.state.current_tool == "polygon":
            self._finish_polygon()

    def _undo_last(self) -> None:
        self._cancel_polygon_preview(reset_points=True)

        if not self.state.history:
            self.status_var.set("Nothing to undo.")
            return

        item_id = self.state.history.pop()
        self.canvas.delete(item_id)
        self.status_var.set("Last action removed.")

    def _clear_canvas(self) -> None:
        if not self.canvas.find_all():
            self.status_var.set("Canvas is already empty.")
            return

        if not messagebox.askyesno("Clear canvas", "Remove everything from the canvas?"):
            return

        self.canvas.delete("all")
        self.state.history.clear()
        self._cancel_polygon_preview(reset_points=True)
        self.status_var.set("Canvas cleared.")

    def _save_canvas(self) -> None:
        file_path = filedialog.asksaveasfilename(
            title="Save drawing",
            defaultextension=".ps",
            filetypes=[("PostScript", "*.ps"), ("EPS", "*.eps")],
            initialfile="drawing.ps",
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            self.canvas.postscript(file=str(path), colormode="color")
        except tk.TclError as error:
            messagebox.showerror("Save failed", f"Could not save drawing.\n\n{error}")
            return

        self.status_var.set(f"Saved drawing to {path.name}")

    def _toggle_fullscreen(self, event: tk.Event[tk.Misc] | None = None) -> None:
        is_zoomed = self.root.state() == "zoomed"
        self.root.state("normal" if is_zoomed else "zoomed")

    def _handle_escape(self, event: tk.Event[tk.Misc] | None = None) -> None:
        if self.state.current_tool == "polygon" and self.state.polygon_points:
            self._cancel_polygon_preview(reset_points=True)
            self.status_var.set("Polygon cancelled.")
            return

        if self.root.state() == "zoomed":
            self.root.state("normal")

    def _handle_return(self, event: tk.Event[tk.Misc] | None = None) -> None:
        if self.state.current_tool == "polygon":
            self._finish_polygon()


def main() -> None:
    root = tk.Tk()
    PaintApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
