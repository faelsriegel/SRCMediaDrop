import os
import platform
import subprocess
import sys
import threading
import time
import webbrowser
import importlib
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

try:
    import tkinter as tk
    from tkinter import messagebox, ttk

    TK_AVAILABLE = True
except Exception:
    tk = None
    messagebox = None
    ttk = None
    TK_AVAILABLE = False

import uvicorn

from app_meta import (
    APP_AUTHOR,
    APP_DISPLAY_NAME,
    APP_LAUNCHER_NAME,
    APP_VERSION,
)
from web_app import app as fastapi_app

try:
    pystray = importlib.import_module("pystray")
    pil_image = importlib.import_module("PIL.Image")
    pil_draw = importlib.import_module("PIL.ImageDraw")
    Image = pil_image
    ImageDraw = pil_draw
    TRAY_AVAILABLE = True
except Exception:
    pystray = None
    Image = None
    ImageDraw = None
    TRAY_AVAILABLE = False

HOST = "127.0.0.1"
PORT = 8000
APP_URL = f"http://{HOST}:{PORT}"
APP_HEALTH_URL = f"{APP_URL}/health"


def is_server_reachable(timeout: float = 1.2) -> bool:
    try:
        with urlopen(APP_HEALTH_URL, timeout=timeout):
            return True
    except URLError:
        return False


class AutoStartManager:
    def __init__(self):
        self.system = platform.system()
        self.launcher_file = Path(__file__).resolve()
        self.python_executable = Path(sys.executable).resolve()

    def _command_parts(self) -> list[str]:
        if getattr(sys, "frozen", False):
            return [str(self.python_executable)]
        return [str(self.python_executable), str(self.launcher_file)]

    def _windows_command(self) -> str:
        return " ".join(f'"{part}"' for part in self._command_parts())

    def _mac_plist_path(self) -> Path:
        return Path.home() / "Library" / "LaunchAgents" / f"com.{APP_LAUNCHER_NAME}.plist"

    def is_enabled(self) -> bool:
        if self.system == "Windows":
            return self._is_enabled_windows()
        if self.system == "Darwin":
            return self._mac_plist_path().exists()
        return False

    def enable(self) -> tuple[bool, str]:
        if self.system == "Windows":
            return self._enable_windows()
        if self.system == "Darwin":
            return self._enable_macos()
        return False, "Autostart não suportado neste sistema."

    def disable(self) -> tuple[bool, str]:
        if self.system == "Windows":
            return self._disable_windows()
        if self.system == "Darwin":
            return self._disable_macos()
        return False, "Autostart não suportado neste sistema."

    def _is_enabled_windows(self) -> bool:
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                value, _ = winreg.QueryValueEx(key, APP_LAUNCHER_NAME)
                return bool(value)
        except Exception:
            return False

    def _enable_windows(self) -> tuple[bool, str]:
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(key, APP_LAUNCHER_NAME, 0, winreg.REG_SZ, self._windows_command())
            return True, "Inicialização automática ativada."
        except Exception as exc:
            return False, f"Falha ao ativar autostart no Windows: {exc}"

    def _disable_windows(self) -> tuple[bool, str]:
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, APP_LAUNCHER_NAME)
            return True, "Inicialização automática desativada."
        except FileNotFoundError:
            return True, "Autostart já estava desativado."
        except Exception as exc:
            return False, f"Falha ao desativar autostart no Windows: {exc}"

    def _enable_macos(self) -> tuple[bool, str]:
        plist_path = self._mac_plist_path()
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        args = "\n".join([f"        <string>{part}</string>" for part in self._command_parts()])
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{APP_LAUNCHER_NAME}</string>
    <key>ProgramArguments</key>
    <array>
{args}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""
        try:
            plist_path.write_text(plist_content, encoding="utf-8")
            subprocess.run(["launchctl", "unload", str(plist_path)], check=False, capture_output=True)
            subprocess.run(["launchctl", "load", str(plist_path)], check=False, capture_output=True)
            return True, "Inicialização automática ativada."
        except Exception as exc:
            return False, f"Falha ao ativar autostart no macOS: {exc}"

    def _disable_macos(self) -> tuple[bool, str]:
        plist_path = self._mac_plist_path()
        try:
            subprocess.run(["launchctl", "unload", str(plist_path)], check=False, capture_output=True)
            if plist_path.exists():
                plist_path.unlink()
            return True, "Inicialização automática desativada."
        except Exception as exc:
            return False, f"Falha ao desativar autostart no macOS: {exc}"


class ServerController:
    def __init__(self):
        self.thread: threading.Thread | None = None
        self.server: uvicorn.Server | None = None
        self.started_by_launcher = False

    def is_running(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    def start(self) -> bool:
        if self.is_running():
            return True

        if is_server_reachable():
            self.started_by_launcher = False
            return True

        config = uvicorn.Config(
            fastapi_app,
            host=HOST,
            port=PORT,
            log_level="warning",
            access_log=False,
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        self.started_by_launcher = True
        return True

    def stop(self) -> bool:
        if not self.started_by_launcher or not self.server:
            return False

        self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=3)

        self.started_by_launcher = False
        self.thread = None
        self.server = None
        return True


class TrayController:
    def __init__(self, app_ref: "LauncherApp"):
        self.app_ref = app_ref
        self.icon = None
        self.thread = None

    def _create_image(self):
        image = Image.new("RGB", (64, 64), color=(11, 16, 32))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 56, 56), radius=10, outline=(64, 220, 255), width=3)
        draw.line((20, 44, 32, 24, 44, 40), fill=(124, 255, 204), width=4)
        return image

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Mostrar", lambda: self.app_ref.run_ui_safe(self.app_ref.show_window)),
            pystray.MenuItem("Iniciar servidor", lambda: self.app_ref.run_ui_safe(self.app_ref.start_server)),
            pystray.MenuItem("Parar servidor", lambda: self.app_ref.run_ui_safe(self.app_ref.stop_server)),
            pystray.MenuItem("Abrir página", lambda: self.app_ref.run_ui_safe(self.app_ref.open_page)),
            pystray.MenuItem("Sair", lambda: self.app_ref.run_ui_safe(self.app_ref.exit_app)),
        )

    def start(self):
        if not TRAY_AVAILABLE or self.icon:
            return

        self.icon = pystray.Icon(APP_LAUNCHER_NAME, self._create_image(), APP_DISPLAY_NAME, self._build_menu())
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.icon:
            self.icon.stop()
            self.icon = None


class TrayOnlyLauncher:
    def __init__(self):
        self.controller = ServerController()
        self.icon = None

    def _create_image(self):
        image = Image.new("RGB", (64, 64), color=(11, 16, 32))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 56, 56), radius=10, outline=(64, 220, 255), width=3)
        draw.line((20, 44, 32, 24, 44, 40), fill=(124, 255, 204), width=4)
        return image

    def _open_page(self):
        if not is_server_reachable():
            self.controller.start()
            time.sleep(0.8)
        webbrowser.open(APP_URL)

    def _start_server(self):
        self.controller.start()

    def _stop_server(self):
        self.controller.stop()

    def _exit(self):
        self.controller.stop()
        if self.icon:
            self.icon.stop()

    def run(self):
        self.controller.start()
        webbrowser.open(APP_URL)

        menu = pystray.Menu(
            pystray.MenuItem("Abrir página", lambda: self._open_page()),
            pystray.MenuItem("Iniciar servidor", lambda: self._start_server()),
            pystray.MenuItem("Parar servidor", lambda: self._stop_server()),
            pystray.MenuItem("Sair", lambda: self._exit()),
        )
        self.icon = pystray.Icon(APP_LAUNCHER_NAME, self._create_image(), APP_DISPLAY_NAME, menu)
        self.icon.run()


class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.controller = ServerController()
        self.autostart = AutoStartManager()
        self.tray = TrayController(self) if TRAY_AVAILABLE else None

        root.title(f"{APP_DISPLAY_NAME} Launcher")
        root.geometry("590x390")
        root.resizable(False, False)
        root.configure(bg="#0b1020")

        self.status_text = tk.StringVar(value="Pronto para iniciar")
        self.auto_start_var = tk.BooleanVar(value=self.autostart.is_enabled())
        self.minimize_to_tray_var = tk.BooleanVar(value=TRAY_AVAILABLE)

        self._build_ui()
        self._poll_status()

        if self.tray:
            self.tray.start()

    def _set_status(self, text: str, color: str = "#74f0d0"):
        self.status_text.set(text)
        self.current_status.configure(fg=color)

    def run_ui_safe(self, callback):
        self.root.after(0, callback)

    def _toggle_autostart(self):
        enabled = self.auto_start_var.get()
        ok, message = self.autostart.enable() if enabled else self.autostart.disable()
        if ok:
            self._set_status(message, "#74f0d0")
        else:
            self.auto_start_var.set(not enabled)
            self._set_status("Falha ao atualizar autostart", "#ff8fb1")
            messagebox.showerror("Autostart", message)

    def _build_ui(self):
        container = tk.Frame(self.root, bg="#0b1020")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(
            container,
            text=APP_DISPLAY_NAME,
            fg="#e9f6ff",
            bg="#0b1020",
            font=("Helvetica", 20, "bold"),
        ).pack(anchor="w")

        tk.Label(
            container,
            text=f"Launcher v{APP_VERSION} • local, rápido e sem terminal.",
            fg="#8fb4d8",
            bg="#0b1020",
            font=("Helvetica", 11),
        ).pack(anchor="w", pady=(2, 16))

        disclaimer = tk.Frame(container, bg="#1a274a", highlightbackground="#3a7ac5", highlightthickness=1)
        disclaimer.pack(fill="x", pady=(0, 12))

        tk.Label(
            disclaimer,
            text="DISCLAIMER",
            fg="#9fd7ff",
            bg="#1a274a",
            font=("Helvetica", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))

        tk.Label(
            disclaimer,
            text=(
                "Este aplicativo é destinado exclusivamente para uso pessoal e educacional. "
                "Respeite direitos autorais e os termos de uso das plataformas."
            ),
            fg="#d5e8ff",
            bg="#1a274a",
            justify="left",
            wraplength=530,
            font=("Helvetica", 10),
        ).pack(anchor="w", padx=12)

        tk.Label(
            disclaimer,
            text=f"Criado por {APP_AUTHOR} • Versão {APP_VERSION}",
            fg="#7fc3ff",
            bg="#1a274a",
            font=("Helvetica", 9, "italic"),
        ).pack(anchor="w", padx=12, pady=(6, 10))

        card = tk.Frame(container, bg="#131f3f", highlightbackground="#245a9c", highlightthickness=1)
        card.pack(fill="x", pady=(0, 12))

        status_row = tk.Frame(card, bg="#131f3f")
        status_row.pack(fill="x", padx=14, pady=(12, 8))
        tk.Label(status_row, text="Status:", fg="#b7d3ee", bg="#131f3f", font=("Helvetica", 11, "bold")).pack(side="left")
        self.current_status = tk.Label(
            status_row,
            textvariable=self.status_text,
            fg="#74f0d0",
            bg="#131f3f",
            font=("Helvetica", 11),
        )
        self.current_status.pack(side="left", padx=(8, 0))

        tk.Label(card, text=APP_URL, fg="#8fe8ff", bg="#131f3f", font=("Courier", 10)).pack(anchor="w", padx=14, pady=(0, 12))

        options = tk.Frame(container, bg="#0b1020")
        options.pack(fill="x", pady=(0, 10))

        ttk.Checkbutton(
            options,
            text="Iniciar com o sistema",
            variable=self.auto_start_var,
            command=self._toggle_autostart,
        ).pack(anchor="w")

        self.tray_check = ttk.Checkbutton(
            options,
            text="Minimizar para bandeja ao fechar",
            variable=self.minimize_to_tray_var,
        )
        self.tray_check.pack(anchor="w", pady=(6, 0))
        if not TRAY_AVAILABLE:
            self.minimize_to_tray_var.set(False)
            self.tray_check.configure(state="disabled")

        buttons = tk.Frame(container, bg="#0b1020")
        buttons.pack(fill="x")
        self.start_btn = ttk.Button(buttons, text="Rodar Servidor", command=self.start_server)
        self.start_btn.pack(side="left", padx=(0, 10))
        self.open_btn = ttk.Button(buttons, text="Abrir Página", command=self.open_page)
        self.open_btn.pack(side="left", padx=(0, 10))
        self.stop_btn = ttk.Button(buttons, text="Parar", command=self.stop_server)
        self.stop_btn.pack(side="left", padx=(0, 10))
        self.exit_btn = ttk.Button(buttons, text="Fechar", command=self.on_close)
        self.exit_btn.pack(side="left")

        tk.Label(
            container,
            text="Dica: Iniciar → Abrir Página. O launcher detecta servidor externo automaticamente.",
            fg="#7c95bb",
            bg="#0b1020",
            font=("Helvetica", 10),
        ).pack(anchor="w", pady=(12, 0))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def wait_until_ready(self, timeout_seconds: float = 8.0) -> bool:
        started_at = time.time()
        while time.time() - started_at < timeout_seconds:
            if is_server_reachable(timeout=1.2):
                return True
            time.sleep(0.2)
        return False

    def start_server(self):
        if is_server_reachable():
            self._set_status("Servidor já está online", "#74f0d0")
            webbrowser.open(APP_URL)
            return

        self._set_status("Iniciando servidor...", "#f6d365")
        self.controller.start()

        def check_ready():
            ready = self.wait_until_ready()
            if ready:
                self.run_ui_safe(lambda: self._set_status("Servidor online", "#74f0d0"))
                webbrowser.open(APP_URL)
            else:
                self.run_ui_safe(lambda: self._set_status("Falha ao iniciar", "#ff8fb1"))
                self.run_ui_safe(
                    lambda: messagebox.showerror(
                        "Erro",
                        "Não foi possível iniciar o servidor local na porta 8000.",
                    )
                )

        threading.Thread(target=check_ready, daemon=True).start()

    def stop_server(self):
        if not self.controller.started_by_launcher:
            self._set_status("Servidor externo em uso (não parado)", "#8fb4d8")
            return

        self._set_status("Parando servidor...", "#f6d365")
        stopped = self.controller.stop()
        if stopped:
            self._set_status("Servidor parado", "#ff8fb1")
        else:
            self._set_status("Nenhum servidor iniciado pelo launcher", "#8fb4d8")

    def open_page(self):
        if is_server_reachable():
            self._set_status("Abrindo aplicação no navegador", "#74f0d0")
            webbrowser.open(APP_URL)
            return

        if messagebox.askyesno("Servidor offline", "Deseja iniciar o servidor agora?"):
            self.start_server()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _poll_status(self):
        reachable = is_server_reachable(timeout=0.5)
        self.start_btn.configure(state=("disabled" if reachable else "normal"))
        self.stop_btn.configure(state=("normal" if self.controller.started_by_launcher else "disabled"))
        self.root.after(500, self._poll_status)

    def exit_app(self):
        self.controller.stop()
        if self.tray:
            self.tray.stop()
        self.root.destroy()

    def on_close(self):
        if self.minimize_to_tray_var.get() and TRAY_AVAILABLE:
            self.root.withdraw()
            self._set_status("App minimizado para bandeja", "#8fb4d8")
            return
        self.exit_app()


def main():
    if platform.system() not in {"Windows", "Darwin"}:
        os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")

    if TK_AVAILABLE:
        root = tk.Tk()
        ttk.Style().theme_use("clam")
        LauncherApp(root)
        root.mainloop()
        return

    if TRAY_AVAILABLE:
        TrayOnlyLauncher().run()
        return

    raise RuntimeError("Interface gráfica indisponível: tkinter e pystray não estão disponíveis.")


if __name__ == "__main__":
    main()
