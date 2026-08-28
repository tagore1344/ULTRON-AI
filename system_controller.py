# system_controller.py
import os
import asyncio
import ctypes
import time
import datetime
import webbrowser
import urllib.parse
import pyautogui
import psutil
import subprocess
import threading

try:
    import screen_brightness_control as sbc
    BRIGHTNESS_OK = True
except ImportError:
    sbc = None
    BRIGHTNESS_OK = False

try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    VOLUME_OK = True
except ImportError:
    AudioUtilities = None
    IAudioEndpointVolume = None
    VOLUME_OK = False

class SystemController:
    def __init__(self, speech):
        self.speech = speech
        self.volume_interface = None
        self._init_volume()

    def _init_volume(self):
        if VOLUME_OK:
            try:
                devices = AudioUtilities.GetSpeakers()
                if hasattr(devices, "EndpointVolume"):
                    self.volume_interface = devices.EndpointVolume
                else:
                    interface = devices.Activate(
                        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
                    )
                    try:
                        self.volume_interface = interface.QueryInterface(IAudioEndpointVolume)
                    except AttributeError:
                        from ctypes import cast, POINTER
                        self.volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                print("[SYSTEM] Volume control ready")
            except Exception as e:
                print(f"[SYSTEM] Volume control error: {e}")

    # ===== VOLUME =====
    def volume_up(self, amount=10):
        if self.volume_interface:
            current = int(self.volume_interface.GetMasterVolumeLevelScalar() * 100)
            new_level = min(100, current + amount)
            self.volume_interface.SetMasterVolumeLevelScalar(new_level / 100, None)
            self.speech.speak(f"Volume {new_level} percent")
        else:
            for _ in range(5):
                pyautogui.press('volumeup')
            self.speech.speak("Volume up")

    def volume_down(self, amount=10):
        if self.volume_interface:
            current = int(self.volume_interface.GetMasterVolumeLevelScalar() * 100)
            new_level = max(0, current - amount)
            self.volume_interface.SetMasterVolumeLevelScalar(new_level / 100, None)
            self.speech.speak(f"Volume {new_level} percent")
        else:
            for _ in range(5):
                pyautogui.press('volumedown')
            self.speech.speak("Volume down")

    def set_volume(self, level):
        level = max(0, min(100, int(level)))
        if self.volume_interface:
            self.volume_interface.SetMasterVolumeLevelScalar(level / 100, None)
        self.speech.speak(f"Volume set to {level} percent")

    def mute(self):
        pyautogui.press('volumemute')
        self.speech.speak("Muted")

    # ===== BRIGHTNESS =====
    def brightness_up(self):
        if BRIGHTNESS_OK:
            try:
                current = sbc.get_brightness()[0]
                sbc.set_brightness(min(100, current + 10))
                self.speech.speak("Brightness increased")
            except Exception as e:
                print(f"[SYSTEM] Brightness up error: {e}")
                self.speech.speak("Could not control brightness")
        else:
            self.speech.speak("Brightness control not available")

    def brightness_down(self):
        if BRIGHTNESS_OK:
            try:
                current = sbc.get_brightness()[0]
                sbc.set_brightness(max(0, current - 10))
                self.speech.speak("Brightness decreased")
            except Exception as e:
                print(f"[SYSTEM] Brightness down error: {e}")
                self.speech.speak("Could not control brightness")
        else:
            self.speech.speak("Brightness control not available")

    def set_brightness(self, level):
        if BRIGHTNESS_OK:
            try:
                sbc.set_brightness(int(level))
                self.speech.speak(f"Brightness set to {level} percent")
            except Exception as e:
                print(f"[SYSTEM] Set brightness error: {e}")
                self.speech.speak("Brightness control failed")
        else:
            self.speech.speak("Brightness control not available")

    # ===== TIME & DATE =====
    def get_time(self):
        now = datetime.datetime.now()
        t = now.strftime("%I:%M %p")
        self.speech.speak(f"The time is {t}")

    def get_date(self):
        now = datetime.datetime.now()
        d = now.strftime("%A, %B %d, %Y")
        self.speech.speak(f"Today is {d}")

    # ===== SYSTEM INFO =====
    def get_battery(self):
        battery = psutil.sensors_battery()
        if battery:
            p = int(battery.percent)
            status = "plugged in" if battery.power_plugged else "on battery"
            self.speech.speak(f"Battery is at {p} percent and {status}")
        else:
            self.speech.speak("No battery detected")

    def get_system_info(self):
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        self.speech.speak(
            f"CPU usage is {cpu} percent. "
            f"RAM usage is {ram.percent} percent."
        )

    # ===== POWER =====
    def shutdown(self):
        self.speech.speak("Shutting down in 5 seconds")
        time.sleep(2)
        subprocess.run(["shutdown", "/s", "/t", "5"], shell=False)

    async def ashutdown(self):
        """Non-blocking variant for async execution paths (FastAPI/gateway)."""
        self.speech.speak("Shutting down in 5 seconds")
        await asyncio.to_thread(time.sleep, 2)
        await asyncio.to_thread(subprocess.run, ["shutdown", "/s", "/t", "5"], shell=False)

    def restart(self):
        self.speech.speak("Restarting in 5 seconds")
        time.sleep(2)
        subprocess.run(["shutdown", "/r", "/t", "5"], shell=False)

    async def arestart(self):
        """Non-blocking variant for async execution paths (FastAPI/gateway)."""
        self.speech.speak("Restarting in 5 seconds")
        await asyncio.to_thread(time.sleep, 2)
        await asyncio.to_thread(subprocess.run, ["shutdown", "/r", "/t", "5"], shell=False)

    def sleep(self):
        self.speech.speak("Going to sleep")
        time.sleep(1)
        subprocess.run(
            ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            shell=False
        )

    async def asleep(self):
        """Non-blocking variant for async execution paths (FastAPI/gateway)."""
        self.speech.speak("Going to sleep")
        await asyncio.to_thread(time.sleep, 1)
        await asyncio.to_thread(
            subprocess.run,
            ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            shell=False,
        )

    def lock_screen(self):
        ctypes.windll.user32.LockWorkStation()
        self.speech.speak("Screen locked")

    async def alock_screen(self):
        """Non-blocking variant for async execution paths (FastAPI/gateway)."""
        await asyncio.to_thread(ctypes.windll.user32.LockWorkStation)
        self.speech.speak("Screen locked")

    def cancel_shutdown(self):
        subprocess.run(["shutdown", "/a"], shell=False)
        self.speech.speak("Shutdown cancelled")

    async def acancel_shutdown(self):
        """Non-blocking variant for async execution paths (FastAPI/gateway)."""
        await asyncio.to_thread(subprocess.run, ["shutdown", "/a"], shell=False)
        self.speech.speak("Shutdown cancelled")

    # ===== MEDIA =====
    def play_pause(self):
        pyautogui.press('playpause')
        self.speech.speak("Play pause")

    def next_track(self):
        pyautogui.press('nexttrack')
        self.speech.speak("Next track")

    def prev_track(self):
        pyautogui.press('prevtrack')
        self.speech.speak("Previous track")

    # ===== WINDOWS =====
    def minimize_all(self):
        pyautogui.hotkey('win', 'd')
        self.speech.speak("Minimized all windows")

    def switch_window(self):
        pyautogui.hotkey('alt', 'tab')

    # ===== WEB =====
    def google_search(self, query):
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        webbrowser.open(url)
        self.speech.speak(f"Searching Google for {query}")

    def open_website(self, url):
        if not url.startswith('http'):
            url = 'https://' + url
        webbrowser.open(url)
        self.speech.speak(f"Opening {url}")

    def youtube_search(self, query):
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        webbrowser.open(url)
        self.speech.speak(f"Searching YouTube for {query}")

    # ===== FILES =====
    def create_folder(self, name):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        path = os.path.join(desktop, name)
        os.makedirs(path, exist_ok=True)
        self.speech.speak(f"Folder {name} created on desktop")

    # ===== CLIPBOARD =====
    def copy(self):
        pyautogui.hotkey('ctrl', 'c')
        self.speech.speak("Copied")

    def paste(self):
        pyautogui.hotkey('ctrl', 'v')
        self.speech.speak("Pasted")

    def undo(self):
        pyautogui.hotkey('ctrl', 'z')
        self.speech.speak("Undone")