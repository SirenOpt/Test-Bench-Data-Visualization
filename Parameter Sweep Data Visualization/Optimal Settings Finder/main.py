# main.py
import tkinter as tk
from app_gui import DataLoaderGUI

if __name__ == "__main__":
    root = tk.Tk()
    app = DataLoaderGUI(root)
    root.mainloop()