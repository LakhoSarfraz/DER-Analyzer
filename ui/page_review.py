import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import docx
from collections import Counter
from ui.dialogs import ProbDialog

class SearchableCombobox(ttk.Combobox):
    """A Combobox that filters its dropdown list as you type."""
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self._values = []
        self.bind('<KeyRelease>', self._on_keyrelease)

    def set_values(self, values):
        self._values = values
        self['values'] = values

    def _on_keyrelease(self, event):
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return', 'Escape', 'Tab'): return
        typed = self.get().lower()
        if typed == '':
            self['values'] = self._values
        else:
            filtered = [v for v in self._values if typed in v.lower()]
            self['values'] = filtered

class ReviewPage(ttk.Frame):
    def __init__(self, parent, main):
        super().__init__(parent)
        self.main = main
        self.rows = []
        self.deleted_stack = []
        self._build_ui()
        self._bind_shortcuts()

    def _build_ui(self):
        layout = ttk.Frame(self, padding=15)
        layout.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(layout)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Step 2: Review & Verify", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        self.summary_label = ttk.Label(header, text="", font=("Segoe UI", 9, "bold"))
        self.summary_label.pack(side=tk.RIGHT)

        # Toolbar
        tb = ttk.Frame(layout)
        tb.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(tb, text="Filter:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar()
        self.filter_var.trace("w", lambda *a: self._rebuild_canvas())
        ttk.Entry(tb, textvariable=self.filter_var, width=25).pack(side=tk.LEFT, padx=(5, 15))
        
        ttk.Label(tb, text="Sort:").pack(side=tk.LEFT)
        self.sort_var = tk.StringVar(value="Original")
        sort_cb = ttk.Combobox(tb, textvariable=self.sort_var, values=["Original", "Confidence ↑", "Confidence ↓"], state="readonly", width=15)
        sort_cb.pack(side=tk.LEFT, padx=(5, 15))
        sort_cb.bind("<<ComboboxSelected>>", lambda e: self._rebuild_canvas())
        
        self.undo_btn = ttk.Button(tb, text="Undo Delete", command=self._undo_delete, state=tk.DISABLED)
        self.undo_btn.pack(side=tk.LEFT, padx=5)
        
        # Bulk Assign
        ttk.Label(tb, text="Bulk assign selected to:").pack(side=tk.LEFT, padx=(20, 5))
        self.bulk_var = tk.StringVar()
        self.bulk_cb = SearchableCombobox(tb, textvariable=self.bulk_var, width=15)
        self.bulk_cb.pack(side=tk.LEFT, padx=5)
        ttk.Button(tb, text="Apply", command=self._bulk_assign).pack(side=tk.LEFT)

        # Canvas for scrolling
        canvas_frame = ttk.Frame(layout)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0, bg="#ffffff")
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable = ttk.Frame(self.canvas)
        
        self.scrollable.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Footer
        footer = ttk.Frame(layout)
        footer.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(footer, text="← Back to Import", command=lambda: self.main._show_page("import")).pack(side=tk.LEFT)
        self.finalize_btn = ttk.Button(footer, text="Finalize, Export & Auto-Train", command=self._on_finalize)
        self.finalize_btn.pack(side=tk.RIGHT)

    def _bind_shortcuts(self):
        self.main.root.bind('<Control-f>', lambda e: self.tk_focusNext())
        self.main.root.bind('<Control-Return>', lambda e: self._on_finalize())
        self.main.root.bind('<Delete>', lambda e: self._delete_selected())
        for i in range(1, 10):
            self.main.root.bind(str(i), lambda e, idx=i: self._assign_shortcut(idx))

    def refresh(self):
        self.bulk_cb.set_values(self.main.engine.categories)

    def load_predictions(self, predictions):
        self.rows.clear()
        self.deleted_stack.clear()
        for p in predictions:
            self.rows.append({
                "text": p["text"],
                "orig_text": p["text"],
                "edited": False,
                "category": "" if p["is_uncertain"] else p["category"],
                "confidence": p["confidence"],
                "uncertain": p["is_uncertain"],
                "top3": p.get("top3", []),
                "selected": tk.BooleanVar(value=False)
            })
        self.filter_var.set("")
        self._rebuild_canvas()

    def _visible_rows(self):
        needle = self.filter_var.get().strip().lower()
        res = [r for r in self.rows if needle in r["text"].lower()] if needle else list(self.rows)
        mode = self.sort_var.get()
        if mode == "Confidence ↑": res.sort(key=lambda r: r["confidence"])
        elif mode == "Confidence ↓": res.sort(key=lambda r: r["confidence"], reverse=True)
        return res

    def _rebuild_canvas(self):
        for w in self.scrollable.winfo_children():
            w.destroy()
            
        visible = self._visible_rows()
        for i, row in enumerate(visible):
            bg = "#fff8e1" if row["uncertain"] else "#ffffff"
            f = tk.Frame(self.scrollable, bg=bg, pady=5, padx=5)
            f.pack(fill=tk.X)
            
            # Checkbox
            tk.Checkbutton(f, variable=row["selected"], bg=bg).pack(side=tk.LEFT, padx=(0, 5))
            
            # Text (Double-click to edit)
            lbl = tk.Label(f, text=row["text"], bg=bg, anchor="w", justify=tk.LEFT, wraplength=500, fg="#4a148c" if row["edited"] else "#000000")
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            def start_edit(event, r=row, l=lbl):
                e = tk.Entry(f, font=("Segoe UI", 9))
                e.insert(0, r["text"])
                e.pack(side=tk.LEFT, fill=tk.X, expand=True)
                l.pack_forget()
                e.focus()
                def save_edit(ev=None):
                    new_txt = e.get().strip()
                    if new_txt:
                        r["text"] = new_txt
                        r["edited"] = (new_txt != r["orig_text"])
                        l.config(text=new_txt, fg="#4a148c" if r["edited"] else "#000000")
                    e.destroy()
                    l.pack(side=tk.LEFT, fill=tk.X, expand=True)
                e.bind("<Return>", save_edit)
                e.bind("<FocusOut>", save_edit)
                
            lbl.bind("<Double-1>", start_edit)

            # Confidence
            c_pct = row["confidence"] * 100 if row["confidence"] > 0 else 0
            c_txt = f"{c_pct:.1f}%" if row["confidence"] > 0 else "—"
            c_lbl = tk.Label(f, text=c_txt, width=8, bg=bg, fg="#b26a00" if row["uncertain"] else "#1b5e20", cursor="hand2")
            c_lbl.pack(side=tk.RIGHT, padx=10)
            if row["top3"]:
                c_lbl.bind("<Button-1>", lambda e, t=row["text"], tp=row["top3"]: ProbDialog(self.main.root, t, tp))

            # Category Dropdown
            cb = SearchableCombobox(f, width=18)
            cb.set_values(self.main.engine.categories)
            cb.set(row["category"])
            cb.pack(side=tk.RIGHT, padx=10)
            cb.bind("<<ComboboxSelected>>", lambda e, r=row, c=cb: r.update({"category": c.get()}))
            cb.bind("<FocusOut>", lambda e, r=row, c=cb: r.update({"category": c.get()}))

            # Delete
            tk.Button(f, text="✕", bg=bg, relief=tk.FLAT, command=lambda r=row: self._delete_row(r)).pack(side=tk.RIGHT)
            
            ttk.Separator(self.scrollable, orient=tk.HORIZONTAL).pack(fill=tk.X)

        self.summary_label.config(text=f"Showing {len(visible)} / {len(self.rows)} paragraphs")
        self.undo_btn.config(state=tk.NORMAL if self.deleted_stack else tk.DISABLED)

    def _delete_row(self, row):
        self.deleted_stack.append(row)
        self.rows.remove(row)
        self._rebuild_canvas()

    def _delete_selected(self):
        to_del = [r for r in self.rows if r["selected"].get()]
        if not to_del: return
        for r in to_del:
            self.deleted_stack.append(r)
            self.rows.remove(r)
        self._rebuild_canvas()

    def _undo_delete(self):
        if not self.deleted_stack: return
        self.rows.append(self.deleted_stack.pop())
        self._rebuild_canvas()

    def _assign_shortcut(self, index):
        cats = self.main.engine.categories
        if index > len(cats): return
        cat = cats[index - 1]
        for r in self.rows:
            if r["selected"].get(): r["category"] = cat
        self._rebuild_canvas()

    def _bulk_assign(self):
        cat = self.bulk_var.get().strip()
        if cat not in self.main.engine.categories:
            messagebox.showwarning("Invalid", "Select a valid category.")
            return
        for r in self.rows:
            if r["selected"].get(): r["category"] = cat
        self._rebuild_canvas()

    def _on_finalize(self):
        approved = []
        for i, r in enumerate(self.rows):
            cat = (r["category"] or "").strip()
            if not cat:
                messagebox.showwarning("Incomplete", f"Row {i+1} has no category.")
                return
            if cat not in self.main.engine.categories:
                messagebox.showwarning("Invalid", f"Row {i+1} category '{cat}' is invalid.")
                return
            approved.append((r["text"], cat))
            
        if not approved: return

        path = filedialog.asksaveasfilename(title="Save Output", defaultextension=".docx", filetypes=[("Word Document", "*.docx")])
        if not path: return
        
        try:
            doc = docx.Document()
            grouped = {}
            for text, cat in approved: grouped.setdefault(cat, []).append(text)
            for cat, paras in grouped.items():
                doc.add_heading(cat, level=2)
                for p in paras: doc.add_paragraph(p)
                doc.add_paragraph("")
            doc.save(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write output:\n{e}")
            return

        self.finalize_btn.config(state=tk.DISABLED)
        try:
            combined = {c for _, c in self.main.engine.dataset} | {c for _, c in approved}
            if len(combined) < 2:
                self.main.engine.dataset.extend(approved)
                if self.main.engine.tmodel_path: self.main.engine.save_model(backup_manager=self.main.backup_manager)
            else:
                self.main.engine.train(approved)
                if self.main.engine.tmodel_path: self.main.engine.save_model(backup_manager=self.main.backup_manager)
                
            self.main.engine.record_export(Counter(c for _, c in approved))
            if self.main.engine.tmodel_path: self.main.engine.save_model(backup_manager=None)
        except Exception as e:
            self.finalize_btn.config(state=tk.NORMAL)
            messagebox.showerror("Training Warning", f"Export saved, but training error:\n{e}")
            return
            
        self.finalize_btn.config(state=tk.NORMAL)
        self.main.pages["import"].text_edit.delete("1.0", tk.END)
        self.main._show_page("import")
        self.main._refresh_ui()
        messagebox.showinfo("Success", f"Exported to:\n{path}\n\nModel retrained.")
