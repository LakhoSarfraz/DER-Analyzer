import os
import tempfile
import glob
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from model_engine import ModelEngine
from storage import Settings, BackupManager, app_dir
from ui.page_import import ImportPage
from ui.page_review import ReviewPage
from ui.page_dataset import DatasetPage
from ui.page_history import HistoryPage
from ui.page_backups import BackupsPage
from ui.page_settings import SettingsPage
from ui.dialogs import NewModelDialog

def _cleanup_orphan_temp():
    try:
        temp_root = tempfile.gettempdir()
        for path in glob.glob(os.path.join(temp_root, "_MEI*")):
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

class MainWindow:
    def __init__(self, root):
        self.root = root
        _cleanup_orphan_temp()
        
        self.root.title("DERClassifier — Offline Paragraph Classifier")
        self.engine = ModelEngine()
        self.settings = Settings()
        self.backup_manager = BackupManager()
        
        self._restore_geometry()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._refresh_ui()

    def _restore_geometry(self):
        w = self.settings.get_int("window_width", 1200)
        h = self.settings.get_int("window_height", 780)
        x = self.settings.get_int("window_x", 100)
        y = self.settings.get_int("window_y", 100)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self.settings.set_int("window_width", self.root.winfo_width())
        self.settings.set_int("window_height", self.root.winfo_height())
        self.settings.set_int("window_x", self.root.winfo_x())
        self.settings.set_int("window_y", self.root.winfo_y())
        self.settings.save()
        self.root.destroy()

    def _build_toolbar(self):
        tb = ttk.Frame(self.root, padding=(10, 8))
        tb.pack(fill=tk.X, side=tk.TOP)
        
        ttk.Button(tb, text="New Model (.tmodel)", command=self._on_new_model).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(tb, text="Load Model (.tmodel)", command=self._on_load_model).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(tb, text="Export / Share Model", command=self._on_export_model).pack(side=tk.LEFT, padx=(0, 15))
        
        self.model_info_label = ttk.Label(tb, text="No model loaded", foreground="#b00020", font=("Segoe UI", 9, "bold"))
        self.model_info_label.pack(side=tk.RIGHT)

    def _build_central(self):
        self.container = ttk.Frame(self.root)
        self.container.pack(fill=tk.BOTH, expand=True)
        
        self.sidebar = ttk.Frame(self.container, width=180)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        self.stack_frame = ttk.Frame(self.container)
        self.stack_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.pages = {
            "import": ImportPage(self.stack_frame, self),
            "review": ReviewPage(self.stack_frame, self),
            "dataset": DatasetPage(self.stack_frame, self),
            "history": HistoryPage(self.stack_frame, self),
            "backups": BackupsPage(self.stack_frame, self),
            "settings": SettingsPage(self.stack_frame, self)
        }
        
        self.sidebar_buttons = {}
        labels = {"import": "Import", "review": "Review", "dataset": "Dataset", "history": "History", "backups": "Backups", "settings": "Settings"}
        for key, label in labels.items():
            btn = ttk.Button(self.sidebar, text=label, command=lambda k=key: self._show_page(k))
            btn.pack(fill=tk.X, padx=5, pady=2)
            self.sidebar_buttons[key] = btn
            
        self.current_page = None
        self._show_page("import")

    def _build_statusbar(self):
        self.status_label = ttk.Label(self.root, text="Ready.", padding=(10, 5))
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM)

    def _show_page(self, key):
        if key in {"review", "dataset", "history", "settings"} and not self.engine.categories:
            self.status_label.config(text="Load or create a model first.")
            self._show_page("import")
            return
            
        if self.current_page:
            self.pages[self.current_page].pack_forget()
            
        self.current_page = key
        self.pages[key].pack(fill=tk.BOTH, expand=True)
        self.pages[key].refresh()

    def _refresh_ui(self):
        has_model = bool(self.engine.categories)
        state = tk.NORMAL if has_model else tk.DISABLED
        
        for key in ["review", "dataset", "history", "settings"]:
            self.sidebar_buttons[key].config(state=state)

        if has_model:
            ready, msg = self.engine.check_readiness()
            total = len(self.engine.dataset)
            thresh = int(round(self.engine.config.get("confidence_threshold", 0.80) * 100))
            cv = self.engine.config.get("cv_accuracy")
            cv_str = f"{cv * 100:.1f}%" if cv is not None else "—"
            fname = os.path.basename(self.engine.tmodel_path) if self.engine.tmodel_path else "Unsaved"
            color = "#1b5e20" if ready else "#b26a00"
            
            self.model_info_label.config(
                text=f"Model: {fname} | Examples: {total} | Threshold: {thresh}% | CV: {cv_str}",
                foreground=color
            )
            self.status_label.config(text=msg)
        else:
            self.model_info_label.config(text="No model loaded", foreground="#b00020")
            self.status_label.config(text="Ready. Create or load a .tmodel file to begin.")
            
        if self.current_page:
            self.pages[self.current_page].refresh()

    def _on_new_model(self):
        path = filedialog.asksaveasfilename(
            title="Create New Model File", defaultextension=".tmodel",
            filetypes=[("Trained Model File", "*.tmodel")], initialdir=app_dir()
        )
        if not path: return
        
        dlg = NewModelDialog(self.root)
        self.root.wait_window(dlg.window)
        if not dlg.result: return
        
        try:
            self.engine = ModelEngine()
            self.engine.create_new_model(dlg.result["categories"], config={
                "confidence_threshold": dlg.result["threshold"],
                "min_examples_per_category": dlg.result["min_examples"]
            })
            self.engine.tmodel_path = path
            self.engine.save_model(backup_manager=None)
            self._refresh_ui()
            self._show_page("import")
            messagebox.showinfo("Success", "New .tmodel file created and ready for your first batch.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not create .tmodel file:\n{e}")

    def _on_load_model(self):
        path = filedialog.askopenfilename(
            title="Open Trained Model File", filetypes=[("Trained Model File", "*.tmodel")], initialdir=app_dir()
        )
        if not path: return
        try:
            self.engine.load_model(path)
            self._refresh_ui()
            self._show_page("import")
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load .tmodel file:\n{e}")

    def _on_export_model(self):
        if not self.engine.categories:
            messagebox.showwarning("No Model", "Create or load a model first.")
            return
        path = filedialog.asksaveasfilename(
            title="Export Portable .tmodel File", defaultextension=".tmodel",
            filetypes=[("Trained Model File", "*.tmodel")], initialdir=app_dir()
        )
        if not path: return
        try:
            orig = self.engine.tmodel_path
            self.engine.save_model(path, backup_manager=None)
            self.engine.tmodel_path = orig
            messagebox.showinfo("Export Complete", f"Portable model saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export model:\n{e}")
