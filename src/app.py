import tkinter as tk
from src.gui.login_window import LoginWindow


def main() -> None:
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()