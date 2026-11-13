import tkinter as tk
from tkinter import ttk, messagebox

class NewModelDialog:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("New Model")
        self.window.geometry("450x480")
        self.window.transient(parent)
        self.window.grab_set()
        self.result = None
        
        frame = ttk.Frame(self.window, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Allowed categories (one per line):", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.cat_text = tk.Text(frame, height=8, width=45)
        self.cat_text.pack(fill=tk.X, pady=(5, 15))
        
        ttk.Label(frame, text="Confidence threshold:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.thresh_var = tk.IntVar(value=80)
        self.slider = ttk.Scale(frame, from_=50, to=99, orient=tk.HORIZONTAL, variable=self.thresh_var, command=self._update_thresh)
        self.slider.pack(fill=tk.X, pady=(5, 0))
        self.thresh_lbl = ttk.Label(frame, text="80%")
        self.thresh_lbl.pack(anchor=tk.E)
        
        ttk.Label(frame, text="Min examples before auto-classify:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(10, 0))
        self.spin = ttk.Spinbox(frame, from_=2, to=20, width=5)
        self.spin.set(5)
        self.spin.pack(anchor=tk.W, pady=(5, 15))
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.window.destroy).pack(side=tk.RIGHT)

    def _update_thresh(self, val):
        self.thresh_lbl.config(text=f"{int(float(val))}%")

    def _save(self):
        raw = self.cat_text.get("1.0", tk.END).strip().splitlines()
        cats = []
        for line in raw:
            c = line.strip()
            if c and c not in cats: cats.append(c)
        if len(cats) < 2:
            messagebox.showerror("Error", "Enter at least 2 distinct categories.", parent=self.window)
            return
        self.result = {
            "categories": cats,
            "threshold": self.thresh_var.get() / 100.0,
            "min_examples": int(self.spin.get())
        }
        self.window.destroy()

class ProbDialog:
    def __init__(self, parent, text, top3):
        self.window = tk.Toplevel(parent)
        self.window.title("Probability Breakdown")
        self.window.geometry("400x220")
        self.window.transient(parent)
        self.window.grab_set()
        
        frame = ttk.Frame(self.window, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        lbl = ttk.Label(frame, text=text[:200] + ("..." if len(text) > 200 else ""), wraplength=370)
        lbl.pack(anchor=tk.W, pady=(0, 15))
        
        for cat, prob in top3:
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=cat).pack(side=tk.LEFT)
            ttk.Label(row, text=f"{prob*100:.1f}%").pack(side=tk.RIGHT)
            
        ttk.Button(frame, text="Close", command=self.window.destroy).pack(pady=10)
