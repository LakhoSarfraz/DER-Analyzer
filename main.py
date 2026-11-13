import os
import sys

# --- FIX FOR PYTHON-DOCX TEMPLATE ERROR ---
if getattr(sys, 'frozen', False):
    # Point python-docx to the extracted _MEIPASS directory
    import docx
    docx.__file__ = os.path.join(sys._MEIPASS, 'docx', '__init__.py')

import tkinter as tk
from tkinterdnd2 import TkinterDnD
from ui.main_window import MainWindow

def main():
    root = TkinterDnD.Tk()
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
