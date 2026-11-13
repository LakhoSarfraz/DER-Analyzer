import tkinter as tk
from tkinter import ttk, messagebox

class SettingsPage(ttk.Frame):
    def __init__(self, parent, main):
        super().__init__(parent)
        self.main = main
        self._building = False
        layout = ttk.Frame(self, padding=20)
        layout.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(layout, text="Settings", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 15))
        
        # Auto-learn toggle
        self.auto_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(layout, text="Auto-learn from new batches (Update model)", variable=self.auto_var).pack(anchor=tk.W, pady=(0, 15))
        
        row1 = ttk.Frame(layout)
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="Confidence Threshold:").pack(side=tk.LEFT)
        self.thresh_var = tk.IntVar(value=80)
        self.slider = ttk.Scale(row1, from_=50, to=99, orient=tk.HORIZONTAL, variable=self.thresh_var, command=self._on_slide)
        self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.thresh_lbl = ttk.Label(row1, text="80%", width=5)
        self.thresh_lbl.pack(side=tk.RIGHT)
        
        row2 = ttk.Frame(layout)
        row2.pack(fill=tk.X, pady=15)
        ttk.Label(row2, text="Min examples before auto-classify:").pack(side=tk.LEFT)
        self.spin = ttk.Spinbox(row2, from_=2, to=20, width=5)
        self.spin.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(layout, text="Save Settings", command=self._save).pack(anchor=tk.W, pady=10)

    def _on_slide(self, val):
        if not self._building:
            self.thresh_lbl.config(text=f"{int(float(val))}%")

    def refresh(self):
        self._building = True
        t = int(round(self.main.engine.config.get("confidence_threshold", 0.80) * 100))
        self.thresh_var.set(t)
        self.thresh_lbl.config(text=f"{t}%")
        self.spin.set(self.main.engine.config.get("min_examples_per_category", 5))
        self.auto_var.set(self.main.engine.config.get("auto_learn", True))
        self._building = False

    def _save(self):
        self.main.engine.config["confidence_threshold"] = self.thresh_var.get() / 100.0
        self.main.engine.config["min_examples_per_category"] = int(self.spin.get())
        self.main.engine.config["auto_learn"] = self.auto_var.get()
        
        if self.main.engine.tmodel_path:
            try:
                self.main.engine.save_model(backup_manager=self.main.backup_manager)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}")
                return
        self.main._refresh_ui()
        messagebox.showinfo("Saved", "Settings saved successfully.")
