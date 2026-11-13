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
        ttk.Button(header, text="Import Word Document (.docx)", command=self._on_import).pack(side=tk.RIGHT)

        hint = ttk.Label(layout, text="Paste paragraphs below. Under 10 words are filtered. You can also drag-and-drop a .docx file.", foreground="#555")
        hint.pack(anchor=tk.W, pady=(0, 5))

        self.text_edit = tk.Text(layout, font=("Segoe UI", 10), wrap=tk.WORD)
        self.text_edit.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Drag and Drop setup
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
        # TkinterDnD returns paths wrapped in braces if they have spaces
        path = event.data.strip('{}')
        if path.lower().endswith(".docx"):
            self._import_docx(path)

    def _on_import(self):
        path = filedialog.askopenfilename(title="Select Word Document", filetypes=[("Word Documents", "*.docx")])
        if path: self._import_docx(path)

    def _import_docx(self, path):
        try:
            paragraphs, stats = extract_paragraphs_from_docx(path)
        except Exception as e:
            messagebox.showerror("Import Error", str(e))
            return
        if not paragraphs:
            messagebox.showinfo("Empty", "No paragraphs with 10+ words found.")
            return
        
        existing = self.text_edit.get("1.0", tk.END).strip()
        combined = (existing + "\n" + "\n".join(paragraphs)).strip() if existing else "\n".join(paragraphs)
        self.text_edit.delete("1.0", tk.END)
        self.text_edit.insert("1.0", combined)
        
        self.main.status_label.config(text=f"Imported {stats['imported']} paragraph(s). Skipped: {stats['headings']} headings, {stats['lists']} list items, {stats['short']} short.")

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
                unique.append(p)
                
        if not unique:
            messagebox.showwarning("No Valid", "No paragraphs meeting the 10-word minimum.")
            return
            
        predictions = self.main.engine.classify_batch(unique)
        self.main.pages["review"].load_predictions(predictions)
        self.main._show_page("review")
