from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from src.gui.dashboard_window import DashboardWindow
from src.service.auth_service import AuthService


class LoginWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AI Camera - Login")
        self.root.geometry("420x240")
        self.root.resizable(False, False)

        self.auth_service = AuthService()

        self.var_username = tk.StringVar(value="admin")
        self.var_password = tk.StringVar(value="123456")

        self.dashboard_toplevel = None
        self.dashboard_screen = None

        self._build_ui()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="AI Camera Dashboard",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(0, 16))

        form = ttk.Frame(outer)
        form.pack(fill="x", pady=8)

        ttk.Label(form, text="Username").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.var_username).grid(
            row=0, column=1, sticky="ew", padx=(12, 0), pady=6
        )

        ttk.Label(form, text="Password").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=self.var_password, show="*").grid(
            row=1, column=1, sticky="ew", padx=(12, 0), pady=6
        )

        form.columnconfigure(1, weight=1)

        btn_row = ttk.Frame(outer)
        btn_row.pack(fill="x", pady=(18, 0))

        ttk.Button(btn_row, text="Login", command=self._on_login).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(btn_row, text="Exit", command=self.root.destroy).pack(side="right")

    def _on_login(self) -> None:
        user = self.auth_service.authenticate(
            self.var_username.get(),
            self.var_password.get(),
        )
        if user is None:
            messagebox.showerror("Login failed", "Sai tài khoản hoặc mật khẩu")
            return

        # Không tạo dashboard trực tiếp trong callback để tránh treo UI
        self.root.after(10, lambda: self._open_dashboard(user))

    def _open_dashboard(self, user: dict) -> None:
        try:
            dashboard = tk.Toplevel(self.root)
            self.dashboard_toplevel = dashboard

            self.dashboard_screen = DashboardWindow(
                dashboard,
                user=user,
                on_logout=self._on_logout,
            )

            # Chỉ ẩn login sau khi dashboard tạo xong
            self.root.withdraw()

            dashboard.deiconify()
            dashboard.lift()
            dashboard.focus_force()

        except Exception as e:
            try:
                if self.dashboard_toplevel is not None:
                    self.dashboard_toplevel.destroy()
            except Exception:
                pass

            self.dashboard_toplevel = None
            self.dashboard_screen = None
            self.root.deiconify()

            messagebox.showerror("Dashboard error", str(e))

    def _on_logout(self) -> None:
        self.dashboard_toplevel = None
        self.dashboard_screen = None
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()