import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import docx
import copy
import os
import sys
from ui.dialogs import ProbDialog

class SearchableCombobox(ttk.Combobox):
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

    def _build_ui(self):
        layout = ttk.Frame(self, padding=15)
        layout.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(layout)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Step 2: Review & Verify", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        self.summary_label = ttk.Label(header, text="", font=("Segoe UI", 9, "bold"))
        self.summary_label.pack(side=tk.RIGHT)

        tb1 = ttk.Frame(layout)
        tb1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(tb1, text="Filter:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar()
        self.filter_var.trace("w", lambda *a: self._rebuild_canvas())
        ttk.Entry(tb1, textvariable=self.filter_var, width=25).pack(side=tk.LEFT, padx=(5, 15))
        
        ttk.Label(tb1, text="Sort:").pack(side=tk.LEFT)
        self.sort_var = tk.StringVar(value="Original")
        sort_cb = ttk.Combobox(tb1, textvariable=self.sort_var, values=["Original", "Confidence ↑", "Confidence ↓", "Invalid First"], state="readonly", width=15)
        sort_cb.pack(side=tk.LEFT, padx=(5, 15))
        sort_cb.bind("<<ComboboxSelected>>", lambda e: self._rebuild_canvas())
        
        self.undo_btn = ttk.Button(tb1, text="Undo Delete", command=self._undo_delete, state=tk.DISABLED)
        self.undo_btn.pack(side=tk.LEFT, padx=5)

        tb2 = ttk.Frame(layout)
        tb2.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(tb2, text="Select All", command=self._select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(tb2, text="Unselect All", command=self._unselect_all).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(tb2, text="Bulk assign selected to:").pack(side=tk.LEFT, padx=(0, 5))
        self.bulk_var = tk.StringVar()
        self.bulk_cb = SearchableCombobox(tb2, textvariable=self.bulk_var, width=15)
        self.bulk_cb.pack(side=tk.LEFT, padx=5)
        ttk.Button(tb2, text="Apply", command=self._bulk_assign).pack(side=tk.LEFT)

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

        footer = ttk.Frame(layout)
        footer.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(footer, text="← Back to Import", command=lambda: self.main._show_page("import")).pack(side=tk.LEFT)
        self.finalize_btn = ttk.Button(footer, text="Finalize & Export", command=self._on_finalize)
        self.finalize_btn.pack(side=tk.RIGHT)

    def refresh(self):
        self.bulk_cb.set_values(self.main.engine.categories)

    def load_items(self, items):
        self.rows.clear()
        self.deleted_stack.clear()
        for item in items:
            item["selected"] = tk.BooleanVar(value=False)
            self.rows.append(item)
        self.filter_var.set("")
        self._rebuild_canvas()

    def _visible_rows(self):
        needle = self.filter_var.get().strip().lower()
        res = [r for r in self.rows if needle in r["text"].lower()] if needle else list(self.rows)
        mode = self.sort_var.get()
        if mode == "Confidence ↑": res.sort(key=lambda r: r["confidence"])
        elif mode == "Confidence ↓": res.sort(key=lambda r: r["confidence"], reverse=True)
        elif mode == "Invalid First": res.sort(key=lambda r: 1 if r["is_valid"] else 0)
        return res

    def _select_all(self):
        for r in self._visible_rows():
            r["selected"].set(True)
        self._rebuild_canvas()

    def _unselect_all(self):
        for r in self._visible_rows():
            r["selected"].set(False)
        self._rebuild_canvas()

    def _rebuild_canvas(self):
        for w in self.scrollable.winfo_children():
            w.destroy()
            
        visible = self._visible_rows()
        for i, row in enumerate(visible):
            if not row["is_valid"]:
                bg = "#ffcdd2" 
            elif row["uncertain"]:
                bg = "#fff8e1" 
            else:
                bg = "#ffffff"
                
            f = tk.Frame(self.scrollable, bg=bg, pady=5, padx=5)
            f.pack(fill=tk.X)
            
            tk.Checkbutton(f, variable=row["selected"], bg=bg).pack(side=tk.LEFT, padx=(0, 5))
            
            lbl = tk.Label(f, text=row["display_text"], bg=bg, anchor="w", justify=tk.LEFT, wraplength=450, fg="#4a148c" if row.get("edited") else "#000000")
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

            c_pct = row["confidence"] * 100 if row["confidence"] > 0 else 0
            c_txt = f"{c_pct:.1f}%" if row["confidence"] > 0 else "—"
            c_lbl = tk.Label(f, text=c_txt, width=7, bg=bg, fg="#b26a00" if row["uncertain"] else "#1b5e20", cursor="hand2")
            c_lbl.pack(side=tk.RIGHT, padx=5)
            if row["top3"]:
                c_lbl.bind("<Button-1>", lambda e, t=row["text"], tp=row["top3"]: ProbDialog(self.main.root, t, tp))

            cb = SearchableCombobox(f, width=16)
            cb.set_values(self.main.engine.categories)
            cb.set(row["category"])
            cb.pack(side=tk.RIGHT, padx=5)
            cb.bind("<<ComboboxSelected>>", lambda e, r=row, c=cb: r.update({"category": c.get()}))
            cb.bind("<FocusOut>", lambda e, r=row, c=cb: r.update({"category": c.get()}))

            tk.Button(f, text="✕", bg=bg, relief=tk.FLAT, command=lambda r=row: self._delete_row(r)).pack(side=tk.RIGHT)
            tk.Button(f, text="✎", bg=bg, relief=tk.FLAT, command=lambda r=row: self._edit_row(r)).pack(side=tk.RIGHT, padx=2)

            ttk.Separator(self.scrollable, orient=tk.HORIZONTAL).pack(fill=tk.X)

        self.summary_label.config(text=f"Showing {len(visible)} / {len(self.rows)} blocks")
        self.undo_btn.config(state=tk.NORMAL if self.deleted_stack else tk.DISABLED)

    def _edit_row(self, row):
        top = tk.Toplevel(self.main.root)
        top.title("Edit Block")
        top.geometry("500x250")
        top.transient(self.main.root)
        
        txt = tk.Text(top, wrap=tk.WORD)
        txt.insert("1.0", row["text"])
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def save(evt=None):
            new = txt.get("1.0", tk.END).strip()
            if new:
                row["text"] = new
                row["display_text"] = new if row["type"] == "paragraph" else new[:100] + "..."
                row["edited"] = True
            top.destroy()
            self._rebuild_canvas()
            
        top.protocol("WM_DELETE_WINDOW", save)
        ttk.Button(top, text="Save", command=save).pack(pady=5)

    def _delete_row(self, row):
        self.deleted_stack.append(row)
        self.rows.remove(row)
        self._rebuild_canvas()

    def _undo_delete(self):
        if not self.deleted_stack: return
        self.rows.append(self.deleted_stack.pop())
        self._rebuild_canvas()

    def _bulk_assign(self):
        cat = self.bulk_var.get().strip()
        if cat not in self.main.engine.categories:
            messagebox.showwarning("Invalid", "Select a valid category.")
            return
            
        assigned_any = False
        for r in self.rows:
            if r["selected"].get(): 
                r["category"] = cat
                r["selected"].set(False) 
                assigned_any = True
                
        if assigned_any:
            self._rebuild_canvas()

    def _on_finalize(self):
        approved = []
        for i, r in enumerate(self.rows):
            cat = (r["category"] or "").strip()
            if not cat:
                messagebox.showwarning("Incomplete", f"Block {i+1} has no category.")
                return
            approved.append(r)
            
        if not approved: return

        path = filedialog.asksaveasfilename(title="Save Output", defaultextension=".docx", filetypes=[("Word Document", "*.docx")])
        if not path: return
        
        try:
            doc = docx.Document()

            grouped = {}
            for item in approved: grouped.setdefault(item["category"], []).append(item)
            
            for cat, items in grouped.items():
                doc.add_heading(cat, level=2)
                for item in items:
                    if item["type"] == "table" and item["obj"] is not None:
                        try:
                            tbl_xml = copy.deepcopy(item["obj"]._tbl)
                            doc.element.body.append(tbl_xml)
                        except Exception:
                            doc.add_paragraph(f"[Table Error: {item['text']}]")
                    else:
                        doc.add_paragraph(item["text"])
                doc.add_paragraph("")
            doc.save(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write output:\n{e}")
            return

        self.finalize_btn.config(state=tk.DISABLED)
        
        if self.main.engine.config.get("auto_learn", True):
            try:
                new_data = [(r["text"], r["category"]) for r in approved]
                combined = {c for _, c in self.main.engine.dataset} | {c for _, c in new_data}
                if len(combined) < 2:
                    self.main.engine.dataset.extend(new_data)
                    if self.main.engine.tmodel_path: self.main.engine.save_model(backup_manager=self.main.backup_manager)
                else:
                    self.main.engine.train(new_data)
                    if self.main.engine.tmodel_path: self.main.engine.save_model(backup_manager=self.main.backup_manager)
            except Exception as e:
                self.finalize_btn.config(state=tk.NORMAL)
                messagebox.showerror("Training Warning", f"Export saved, but training error:\n{e}")
                return
        else:
            if self.main.engine.tmodel_path:
                self.main.engine.save_model(backup_manager=self.main.backup_manager)
                
        self.finalize_btn.config(state=tk.NORMAL)
        self.main.pages["import"].text_edit.delete("1.0", tk.END)
        self.main._show_page("import")
        self.main._refresh_ui()
        messagebox.showinfo("Success", f"Exported to:\n{path}\n\nModel retrained." if self.main.engine.config.get("auto_learn", True) else "Exported successfully.")
