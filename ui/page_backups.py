import tkinter as tk
from tkinter import ttk, messagebox
import os

class BackupsPage(ttk.Frame):
    def __init__(self, parent, main):
        super().__init__(parent)
        self.main = main
        layout = ttk.Frame(self, padding=15)
        layout.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(layout, text="Model Backups (Max 3)", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(layout, text="Stored in %APPDATA%\\DER Analyzer\\backups", foreground="#555").pack(anchor=tk.W, pady=(0, 10))
        
        cols = ("name", "size", "action")
        self.tree = ttk.Treeview(layout, columns=cols, show="headings")
        self.tree.heading("name", text="Backup File")
        self.tree.heading("size", text="Size")
        self.tree.heading("action", text="")
        self.tree.column("name", width=300)
        self.tree.column("size", width=80)
        self.tree.column("action", width=100)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        if not self.main.engine.tmodel_path:
            self.tree.insert("", tk.END, values=("Load a model to see backups.", "", ""))
            return
            
        base = os.path.splitext(os.path.basename(self.main.engine.tmodel_path))[0]
        backups = self.main.backup_manager.list_backups(base)
        if not backups:
            self.tree.insert("", tk.END, values=("No backups yet.", "", ""))
            return
            
        for b in backups:
            size = b["size"] / 1024
            self.tree.insert("", tk.END, values=(b["name"], f"{size:.1f} KB", "Double-click to Restore"), tags=(b["path"],))
            
        self.tree.bind("<Double-1>", self._restore)

    def _restore(self, event):
        sel = self.tree.selection()
        if not sel: return
        item = self.tree.item(sel[0])
        if not item.get("tags"): return
        path = item["tags"][0]
        
        if messagebox.askyesno("Restore", "Overwrite current model with this backup?"):
            try:
                if self.main.engine.tmodel_path and os.path.exists(self.main.engine.tmodel_path):
                    self.main.backup_manager.create_backup(self.main.engine.tmodel_path)
                self.main.engine.load_model(path)
                if self.main.engine.tmodel_path:
                    self.main.engine.save_model(backup_manager=None)
                self.main._refresh_ui()
                messagebox.showinfo("Restored", "Backup loaded successfully.")
            except Exception as e:
                messagebox.showerror("Error", str(e))
