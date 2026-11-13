import tkinter as tk
from tkinter import ttk

class HistoryPage(ttk.Frame):
    def __init__(self, parent, main):
        super().__init__(parent)
        self.main = main
        layout = ttk.Frame(self, padding=15)
        layout.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(layout, text="Export History (last 30)", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        cols = ("time", "total", "per_cat", "cv", "thresh")
        self.tree = ttk.Treeview(layout, columns=cols, show="headings")
        self.tree.heading("time", text="Timestamp")
        self.tree.heading("total", text="Total")
        self.tree.heading("per_cat", text="Per Category")
        self.tree.heading("cv", text="CV")
        self.tree.heading("thresh", text="Thresh")
        self.tree.column("time", width=150)
        self.tree.column("total", width=50)
        self.tree.column("per_cat", width=300)
        self.tree.column("cv", width=70)
        self.tree.column("thresh", width=70)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        hist = list(self.main.engine.config.get("export_history", []))
        hist.reverse()
        for h in hist:
            counts = ", ".join(f"{k}: {v}" for k, v in h.get("counts", {}).items())
            cv = h.get("cv_accuracy")
            cv_s = f"{cv*100:.1f}%" if cv is not None else "—"
            t = h.get("threshold")
            t_s = f"{int(t*100)}%" if t else "—"
            self.tree.insert("", tk.END, values=(h.get("timestamp", ""), h.get("total", 0), counts, cv_s, t_s))
