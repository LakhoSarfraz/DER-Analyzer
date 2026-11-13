import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES
from doc_parser import extract_paragraphs_from_docx

class ImportPage(ttk.Frame):
    def __init__(self, parent, main):
        super().__init__(parent)
        self.main = main
        self._build_ui()

    def _build_ui(self):
        layout = ttk.Frame(self, padding=20)
        layout.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(layout)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Step 1: Import or Paste Paragraphs", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        ttk.Button(header, text="Import Word Document (.docx / .doc)", command=self._on_import).pack(side=tk.RIGHT)

        hint = ttk.Label(layout, text="Paste paragraphs below. Under 10 words are filtered. You can also drag-and-drop a document.", foreground="#555")
        hint.pack(anchor=tk.W, pady=(0, 5))

        self.text_edit = tk.Text(layout, font=("Segoe UI", 10), wrap=tk.WORD)
        self.text_edit.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.text_edit.drop_target_register(DND_FILES)
        self.text_edit.dnd_bind('<<Drop>>', self._on_drop)

        action = ttk.Frame(layout)
        action.pack(fill=tk.X)
        ttk.Button(action, text="Clear Text", command=lambda: self.text_edit.delete("1.0", tk.END)).pack(side=tk.LEFT)
        self.btn_classify = ttk.Button(action, text="Classify Paragraphs →", command=self._on_classify)
        self.btn_classify.pack(side=tk.RIGHT)

    def refresh(self):
        state = tk.NORMAL if self.main.engine.categories else tk.DISABLED
        self.text_edit.config(state=state)
        self.btn_classify.config(state=state)

    def _on_drop(self, event):
        path = event.data.strip('{}')
        if path.lower().endswith((".docx", ".doc")):
            self._import_docx(path)

    def _on_import(self):
        path = filedialog.askopenfilename(title="Select Document", filetypes=[("Word Documents", "*.docx *.doc")])
        if path: self._import_docx(path)

    def _import_docx(self, path):
        try:
            items, stats = extract_paragraphs_from_docx(path)
        except Exception as e:
            messagebox.showerror("Import Error", str(e))
            return
        if not items:
            messagebox.showinfo("Empty", "No valid paragraphs or tables found.")
            return
            
        predictions = self.main.engine.classify_batch([i["text"] for i in items])
        
        # Merge parsed structure with predictions
        for item, pred in zip(items, predictions):
            item["category"] = "" if pred["is_uncertain"] else pred["category"]
            item["confidence"] = pred["confidence"]
            item["uncertain"] = pred["is_uncertain"]
            item["top3"] = pred.get("top3", [])
            
        self.main.pages["review"].load_items(items)
        self.main._show_page("review")
        self.main.status_label.config(text=f"Imported {stats['imported']} block(s). Skipped: {stats['headings']} headings, {stats['short']} short.")

    def _on_classify(self):
        raw = self.text_edit.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showwarning("No Text", "Please paste text or import a file.")
            return
            
        seen = set()
        unique = []
        for line in raw.splitlines():
            p = line.strip()
            if p and len(p.split()) >= 10 and p not in seen:
                seen.add(p)
                # Validate pasted text manually
                from doc_parser import VALIDATION_RE
                is_valid = bool(VALIDATION_RE.match(p))
                unique.append({
                    "type": "paragraph", "text": p, "display_text": p, "is_valid": is_valid, "obj": None
                })
                
        if not unique:
            messagebox.showwarning("No Valid", "No paragraphs meeting the 10-word minimum.")
            return
            
        predictions = self.main.engine.classify_batch([i["text"] for i in unique])
        
        for item, pred in zip(unique, predictions):
            item["category"] = "" if pred["is_uncertain"] else pred["category"]
            item["confidence"] = pred["confidence"]
            item["uncertain"] = pred["is_uncertain"]
            item["top3"] = pred.get("top3", [])
            
        self.main.pages["review"].load_items(unique)
        self.main._show_page("review")
