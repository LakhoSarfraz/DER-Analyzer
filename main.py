import tkinter as tk
from tkinterdnd2 import TkinterDnD
from ui.main_window import MainWindow

def main():
    root = TkinterDnD.Tk()
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
