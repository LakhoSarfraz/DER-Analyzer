import os
import sys

# Fix for python-docx template loading in PyInstaller onefile
if getattr(sys, 'frozen', False):
    try:
        import docx
        if hasattr(sys, '_MEIPASS'):
            docx.__file__ = os.path.join(sys._MEIPASS, 'docx', '__init__.py')
    except Exception:
        pass

import tkinter as tk
from tkinterdnd2 import TkinterDnD
from ui.main_window import MainWindow

def main():
    root = TkinterDnD.Tk()
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
