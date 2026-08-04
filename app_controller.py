# app_controller.py  — FIXED VERSION
import subprocess
import os
import glob
import psutil
import time
from config import CONFIG

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    import pygetwindow as gw
except Exception:
    gw = None

try:
    import winreg
except Exception:
    winreg = None

class AppController:
    def __init__(self, speech):
        self.speech   = speech
        self.username = os.environ.get("USERNAME", "")

        # ── Built-in Windows commands ────────────
        self.win_commands = {
            "notepad":        "notepad.exe",
            "calculator":     "calc.exe",
            "calc":           "calc.exe",
            "paint":          "mspaint.exe",
            "wordpad":        "write.exe",
            "explorer":       "explorer.exe",
            "file explorer":  "explorer.exe",
            "cmd":            "cmd.exe",
            "command prompt": "cmd.exe",
            "powershell":     "powershell.exe",
            "task manager":   "taskmgr.exe",
            "control panel":  "control.exe",
            "settings":       "ms-settings:",
            "snipping tool":  "SnippingTool.exe",
            "magnifier":      "magnify.exe",
            "narrator":       "narrator.exe",
            "on screen keyboard": "osk.exe",
            "character map":  "charmap.exe",
            "registry":       "regedit.exe",
            "disk cleanup":   "cleanmgr.exe",
            "defrag":         "dfrgui.exe",
            "device manager": "devmgmt.msc",
            "services":       "services.msc",
            "event viewer":   "eventvwr.msc",
            "group policy":   "gpedit.msc",
        }

        # ── Windows Store apps ───────────────────
        self.store_apps = {
            "whatsapp":   "whatsapp:",
            "spotify":    "spotify:",
            "netflix":    "netflix:",
            "disney":     "disney+:",
            "xbox":       "xbox:",
            "teams":      "msteams:",
            "skype":      "skype:",
            "onenote":    "onenote:",
            "mail":       "outlookmail:",
            "calendar":   "outlookcal:",
            "maps":       "bingmaps:",
            "camera":     "microsoft.windows.camera:",
            "photos":     "ms-photos:",
            "clock":      "ms-clock:",
            "weather":    "msnweather:",
            "news":       "bingnews:",
            "store":      "ms-windows-store:",
            "phone link": "ms-phone:",
        }

        # ── Browser shortcuts ────────────────────
        self.browsers = {
            "chrome":          self._find_chrome(),
            "google chrome":   self._find_chrome(),
            "firefox":         self._find_firefox(),
            "mozilla firefox": self._find_firefox(),
            "edge":            self._find_edge(),
            "microsoft edge":  self._find_edge(),
            "brave":           self._find_brave(),
            "opera":           self._find_opera(),
        }

        # ── Common app paths ────────────────────
        self.app_paths = self._build_app_paths()

        print("[APPS] App controller ready!")

    # ── Path Finders ────────────────────────────
    def _find_chrome(self):
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.environ.get("LOCALAPPDATA",""),
                         r"Google\Chrome\Application\chrome.exe"),
        ]
        return self._first_exists(paths)

    def _find_firefox(self):
        paths = [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        ]
        return self._first_exists(paths)

    def _find_edge(self):
        paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        return self._first_exists(paths)

    def _find_brave(self):
        paths = [
            os.path.join(os.environ.get("LOCALAPPDATA",""),
                         r"BraveSoftware\Brave-Browser\Application\brave.exe"),
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        ]
        return self._first_exists(paths)

    def _find_opera(self):
        paths = [
            os.path.join(os.environ.get("LOCALAPPDATA",""),
                         r"Programs\Opera\opera.exe"),
            r"C:\Program Files\Opera\opera.exe",
        ]
        return self._first_exists(paths)

    def _first_exists(self, paths):
        for p in paths:
            if p and os.path.exists(p):
                return p
        return None

    def _build_app_paths(self):
        """Scan common locations for apps."""
        apps = {}
        u    = self.username
        la   = os.environ.get("LOCALAPPDATA", "")
        ap   = os.environ.get("APPDATA", "")

        candidates = {
            # Microsoft Office
            "word":       [
                r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
                r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
                r"C:\Program Files\Microsoft Office\Office16\WINWORD.EXE",
            ],
            "excel":      [
                r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
                r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
            ],
            "powerpoint": [
                r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
                r"C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE",
            ],
            "outlook":    [
                r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
                r"C:\Program Files (x86)\Microsoft Office\root\Office16\OUTLOOK.EXE",
            ],
            "access":     [
                r"C:\Program Files\Microsoft Office\root\Office16\MSACCESS.EXE",
            ],

            # Media
            "vlc":        [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            ],
            "media player": [
                r"C:\Program Files\Windows Media Player\wmplayer.exe",
            ],
            "itunes":     [
                r"C:\Program Files\iTunes\iTunes.exe",
                r"C:\Program Files (x86)\iTunes\iTunes.exe",
            ],
            "pot player": [
                r"C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe",
            ],

            # Development
            "vscode":     [
                os.path.join(la, r"Programs\Microsoft VS Code\Code.exe"),
                r"C:\Program Files\Microsoft VS Code\Code.exe",
            ],
            "visual studio code": [
                os.path.join(la, r"Programs\Microsoft VS Code\Code.exe"),
            ],
            "android studio": [
                r"C:\Program Files\Android\Android Studio\bin\studio64.exe",
            ],
            "pycharm":    [
                os.path.join(la, r"JetBrains\PyCharm*\bin\pycharm64.exe"),
            ],
            "sublime":    [
                r"C:\Program Files\Sublime Text\sublime_text.exe",
                r"C:\Program Files\Sublime Text 3\sublime_text.exe",
            ],

            # Communication
            "discord":    [
                os.path.join(la, r"Discord\Update.exe"),
                os.path.join(ap, r"Discord\Discord.exe"),
            ],
            "telegram":   [
                os.path.join(ap, r"Telegram Desktop\Telegram.exe"),
                os.path.join(la, r"Telegram Desktop\Telegram.exe"),
            ],
            "zoom":       [
                os.path.join(ap, r"Zoom\bin\Zoom.exe"),
            ],
            "slack":      [
                os.path.join(la, r"slack\slack.exe"),
            ],

            # Gaming
            "steam":      [
                r"C:\Program Files (x86)\Steam\steam.exe",
                r"C:\Program Files\Steam\steam.exe",
            ],
            "epic games": [
                os.path.join(la, r"EpicGamesLauncher\Portal\Binaries\Win64\EpicGamesLauncher.exe"),
            ],
            "riot client":[
                os.path.join(la, r"Riot Games\Riot Client\RiotClientServices.exe"),
            ],
            "minecraft":  [
                os.path.join(la, r"Packages\Microsoft.MinecraftUWP_*\LocalState"),
            ],

            # Creative
            "obs":        [
                r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
                r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe",
            ],
            "photoshop":  [
                r"C:\Program Files\Adobe\Adobe Photoshop*\Photoshop.exe",
            ],
            "premiere":   [
                r"C:\Program Files\Adobe\Adobe Premiere Pro*\Adobe Premiere Pro.exe",
            ],
            "audacity":   [
                r"C:\Program Files\Audacity\Audacity.exe",
            ],
            "blender":    [
                r"C:\Program Files\Blender Foundation\Blender*\blender.exe",
            ],

            # Utilities
            "winrar":     [
                r"C:\Program Files\WinRAR\WinRAR.exe",
            ],
            "7zip":       [
                r"C:\Program Files\7-Zip\7zFM.exe",
            ],
            "ccleaner":   [
                r"C:\Program Files\CCleaner\CCleaner64.exe",
            ],
            "malwarebytes": [
                r"C:\Program Files\Malwarebytes\Anti-Malware\mbam.exe",
            ],
        }

        for name, paths in candidates.items():
            for path in paths:
                if "*" in path:
                    matches = glob.glob(path)
                    if matches:
                        apps[name] = matches[0]
                        break
                elif path and os.path.exists(path):
                    apps[name] = path
                    break

        return apps

    # ── Registry Search ─────────────────────────
    def _search_registry(self, app_name):
        """Search Windows registry for installed apps."""
        reg_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
        ]

        if winreg is None:
            return None

        for reg_path in reg_paths:
            for hive in [winreg.HKEY_LOCAL_MACHINE,
                         winreg.HKEY_CURRENT_USER]:
                try:
                    key = winreg.OpenKey(hive, reg_path)
                    count = winreg.QueryInfoKey(key)[0]
                    for i in range(count):
                        try:
                            sub_name = winreg.EnumKey(key, i)
                            sub_key  = winreg.OpenKey(key, sub_name)
                            try:
                                display = winreg.QueryValueEx(
                                    sub_key, "DisplayName"
                                )[0].lower()
                                if app_name in display:
                                    try:
                                        path = winreg.QueryValueEx(
                                            sub_key,
                                            "InstallLocation"
                                        )[0]
                                        if path and os.path.exists(path):
                                            for f in os.listdir(path):
                                                if f.endswith(".exe"):
                                                    return os.path.join(path, f)
                                    except:
                                        pass
                            except:
                                pass
                            try:
                                path = winreg.QueryValueEx(
                                    sub_key, ""
                                )[0]
                                if (path and os.path.exists(path)
                                        and app_name in sub_name.lower()):
                                    return path
                            except:
                                pass
                        except:
                            continue
                except:
                    continue
        return None

    # ── Main Open Method ────────────────────────
    def open_app(self, app_name: str):
        app_name = app_name.lower().strip()

        # Clean common speech artifacts
        for word in ["the", "app", "application",
                     "program", "software", "please",
                     "open", "launch", "start", "run"]:
            app_name = app_name.replace(word + " ", "").strip()
            if app_name.endswith(" " + word):
                app_name = app_name[:-len(word)-1].strip()

        print(f"[APPS] Opening: '{app_name}'")

        # ── 1. Windows built-in commands ────────
        for key, cmd in self.win_commands.items():
            if key in app_name or app_name in key:
                if cmd.endswith(":"):
                    try:
                        os.startfile(cmd)
                    except Exception:
                        subprocess.Popen(cmd, shell=True)
                else:
                    try:
                        subprocess.Popen(cmd, shell=True)
                    except Exception:
                        subprocess.Popen(cmd, shell=True)
                self.speech.speak(f"Opening {key}")
                return True

        # ── 2. Windows Store apps ────────────────
        for key, protocol in self.store_apps.items():
            if key in app_name or app_name in key:
                try:
                    os.startfile(protocol)
                    self.speech.speak(f"Opening {key}")
                    return True
                except:
                    pass

        # ── 3. Browser shortcuts ─────────────────
        for key, path in self.browsers.items():
            if key in app_name or app_name in key:
                if path and os.path.exists(path):
                    subprocess.Popen([path])
                    self.speech.speak(f"Opening {key}")
                    return True

        # ── 4. Scanned app paths ─────────────────
        for key, path in self.app_paths.items():
            if key in app_name or app_name in key:
                if path and os.path.exists(path):
                    subprocess.Popen([path])
                    self.speech.speak(f"Opening {key}")
                    return True

        # ── 5. Config apps ───────────────────────
        config_apps = CONFIG.get("apps", {})
        for key, path in config_apps.items():
            path = path.replace("{username}", self.username)
            if key in app_name or app_name in key:
                if "*" in path:
                    matches = glob.glob(path)
                    path = matches[0] if matches else path
                if os.path.exists(path):
                    subprocess.Popen([path])
                    self.speech.speak(f"Opening {key}")
                    return True

        # ── 6. Registry search ───────────────────
        reg_path = self._search_registry(app_name)
        if reg_path:
            subprocess.Popen([reg_path])
            self.speech.speak(f"Opening {app_name}")
            return True

        # ── 7. Windows shell / start command ─────
        try:
            result = subprocess.run(
                f'start "" "{app_name}"',
                shell=True,
                capture_output=True,
                timeout=3
            )
            if result.returncode == 0:
                self.speech.speak(f"Opening {app_name}")
                return True
        except:
            pass

        # ── 8. Try as executable directly ────────
        try:
            subprocess.Popen(
                f"{app_name}.exe",
                shell=True
            )
            self.speech.speak(f"Opening {app_name}")
            return True
        except:
            pass

        # ── 9. Search Start Menu ─────────────────
        self._search_start_menu(app_name)
        return False

    def _search_start_menu(self, app_name):
        """Search and open from Start Menu."""
        start_menu_paths = [
            os.path.join(
                os.environ.get("APPDATA", ""),
                r"Microsoft\Windows\Start Menu\Programs"
            ),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        ]

        for start_path in start_menu_paths:
            for root, dirs, files in os.walk(start_path):
                for f in files:
                    if (f.endswith(".lnk")
                            and app_name in f.lower()):
                        full = os.path.join(root, f)
                        os.startfile(full)
                        self.speech.speak(
                            f"Opening {f.replace('.lnk','')}"
                        )
                        return True

        # Nothing found
        self.speech.speak(
            f"I could not find {app_name}. "
            "Try saying the exact app name."
        )
        return False

    def close_app(self, app_name: str):
        app_name = app_name.lower().strip()
        closed   = False

        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                pname = proc.info["name"].lower().replace(".exe","")
                if app_name in pname or pname in app_name:
                    proc.terminate()
                    closed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Also close by window title
        if gw is not None:
            try:
                for w in gw.getAllWindows():
                    if app_name in w.title.lower():
                        w.close()
                        closed = True
            except:
                pass

        self.speech.speak(
            f"Closed {app_name}" if closed
            else f"{app_name} is not running"
        )

    def switch_to_app(self, app_name: str):
        app_name = app_name.lower()
        if gw is None:
            self.speech.speak(f"Could not find {app_name} window")
            return False

        for w in gw.getAllWindows():
            if app_name in w.title.lower() and w.title:
                try:
                    w.activate()
                    time.sleep(0.3)
                    w.activate()
                    self.speech.speak(f"Switched to {app_name}")
                    return True
                except:
                    pass
        self.speech.speak(f"Could not find {app_name} window")
        return False

    def take_screenshot(self):
        ts = time.strftime("%Y%m%d_%H%M%S")
        name = f"screenshot_{ts}.png"
        if pyautogui is not None:
            try:
                pyautogui.screenshot().save(name)
                self.speech.speak("Screenshot saved")
                return name
            except Exception:
                pass
        self.speech.speak("Screenshot feature unavailable in this environment")
        return name

    def list_open_windows(self):
        windows = []
        if gw is not None:
            windows = [w.title for w in gw.getAllWindows() if w.title.strip()]
        if windows:
            names = ", ".join(windows[:8])
            self.speech.speak(f"Open windows: {names}")
        else:
            self.speech.speak("No open windows found")
        return windows