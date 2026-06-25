# run_ultron.py
import sys
from PyQt6.QtWidgets import QApplication
from assistant_with_brain import JarvisWithBrain
from transparent_overlay import UltronTopOverlay

if __name__ == "__main__":
    print("[DEBUG 1] Starting application on main thread thread context...")
    
    # 1. Initialize the required QApplication directly on the Main Thread
    app = QApplication(sys.argv)
    
    print("[DEBUG 2] Compiling backend AI configurations...")
    # 2. Instantiate our background assistant logic agent
    bot = JarvisWithBrain()
    
    print("[DEBUG 3] Rendering display overlays...")
    # 3. Instantiate the display layer window safely on the Main Thread
    overlay = UltronTopOverlay()
    overlay.show()
    
    # 4. Link the interface handles together
    bot.inject_overlay(overlay)
    
    print("[DEBUG 4] Spawning microphone loops into the background...")
    # 5. Kick off audio tracking inside its separate background sequence
    bot.start()
    
    print("[DEBUG 5] Handing control over to windows display handles.")
    # 6. Execute the continuous main window frame manager
    sys.exit(app.exec())