import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from collections import Counter

class DatasetPage(ttk.Frame):
    def __init__(self, parent, main):
        super().__init__(parent)
        self.main = main
        self._build_ui()

    def _build_ui(self):
        layout = ttk.Frame(self, padding=15)
        layout.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(layout, text="Dataset Health", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)
        self.summary = ttk.Label(layout, text="")
        self.summary.pack(anchor=tk.W, pady=(0, 10))
        
        cols = ("cat", "count", "status", "note")
        self.tree = ttk.Treeview(layout, columns=cols, show="headings", height=8)
        self.tree.heading("cat", text="Category")
        self.tree.heading("count", text="Examples")
        self.tree.heading("status", text="Status")
        self.tree.heading("note", text="What this means")
        self.tree.column("cat", width=120)
        self.tree.column("count", width=60)
        self.tree.column("status", width=70)
        self.tree.column("note", width=300)
        self.tree.pack(fill=tk.X, pady=(0, 10))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        
        btn_bar = ttk.Frame(layout)
        btn_bar.pack(fill=tk.X, pady=5)
        self.btn_ren = ttk.Button(btn_bar, text="Rename...", command=self._rename, state=tk.DISABLED)
        self.btn_ren.pack(side=tk.LEFT, padx=5)
        self.btn_del = ttk.Button(btn_bar, text="Delete...", command=self._delete, state=tk.DISABLED)
        self.btn_del.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(btn_bar, text="Merge into:").pack(side=tk.LEFT, padx=(20, 5))
        self.merge_var = tk.StringVar()
        self.merge_cb = ttk.Combobox(btn_bar, textvariable=self.merge_var, state="readonly", width=15)
        self.merge_cb.pack(side=tk.LEFT)
        ttk.Button(btn_bar, text="Merge →", command=self._merge).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(layout, text="Examples in selected category:").pack(anchor=tk.W, pady=(10, 5))
        self.listbox = tk.Listbox(layout, height=8, font=("Segoe UI", 9))
        self.listbox.pack(fill=tk.BOTH, expand=True)

    def refresh(self):
        cats = self.main.engine.categories
        counts = Counter(c for _, c in self.main.engine.dataset)
        min_req = self.main.engine.config.get("min_examples_per_category", 5)
        cv = self.main.engine.config.get("cv_accuracy")
        small = self.main.engine.config.get("cv_small_data", False)
        
        cv_txt = f"{cv*100:.1f}%" if cv is not None else "—"
        if cv is not None and small: cv_txt += " (approximate)"
        self.summary.config(text=f"Categories: {len(cats)} | Total examples: {len(self.main.engine.dataset)} | Last CV: {cv_txt}")
        
        self.tree.delete(*self.tree.get_children())
        self.merge_cb['values'] = cats
        if cats: self.merge_cb.current(0)
        self.listbox.delete(0, tk.END)
        
        for cat in cats:
            cnt = counts.get(cat, 0)
            status = "✅ OK" if cnt >= min_req else "⚠ Low"
            if cnt < min_req: note = f"Will output 'Uncertain' until ~{min_req*2} examples."
            elif len(self.main.engine.dataset) < 30: note = "Small dataset overall."
            else: note = "—"
            self.tree.insert("", tk.END, values=(cat, cnt, status, note))
            
        self.btn_ren.config(state=tk.DISABLED)
        self.btn_del.config(state=tk.DISABLED)

    def _get_selected(self):
        sel = self.tree.selection()
        if not sel: return None
        return self.tree.item(sel[0])['values'][0]

    def _on_select(self, event):
        cat = self._get_selected()
        if not cat: return
        self.btn_ren.config(state=tk.NORMAL)
        self.btn_del.config(state=tk.NORMAL)
        self.listbox.delete(0, tk.END)
        for text, c in self.main.engine.dataset:
            if c == cat: self.listbox.insert(tk.END, text)

    def _rename(self):
        cat = self._get_selected()
        if not cat: return
        new = simpledialog.askstring("Rename", f"New name for '{cat}':", initialvalue=cat, parent=self)
        if new and new != cat:
            try:
                self.main.engine.rename_category(cat, new)
                self._save()
            except Exception as e: messagebox.showerror("Error", str(e))

    def _delete(self):
        cat = self._get_selected()
        if not cat: return
        cnt = sum(1 for _, c in self.main.engine.dataset if c == cat)
        if messagebox.askyesno("Delete", f"Delete '{cat}' and remove {cnt} examples?"):
            try:
                self.main.engine.delete_category(cat)
                self._save()
            except Exception as e: messagebox.showerror("Error", str(e))

    def _merge(self):
        src = self._get_selected()
        tgt = self.merge_var.get()
        if not src or not tgt or src == tgt: return
        if messagebox.askyesno("Merge", f"Merge '{src}' into '{tgt}'?"):
            try:
                self.main.engine.merge_categories([src], tgt)
                self._save()
            except Exception as e: messagebox.showerror("Error", str(e))

    def _save(self):
        if self.main.engine.tmodel_path:
            try: self.main.engine.save_model(backup_manager=self.main.backup_manager)
            except Exception: pass
        self.main._refresh_ui()
