# main_advanced.py — Run Advanced ULTRON with AI Brain
import sys
import os
import time
from assistant_with_brain import JarvisWithBrain

if __name__ == "__main__":
    print("\n" + "="*60)
    print("   🧠 ULTRON — Advanced AI Brain Edition")
    print("   WELCOME TO THE FUTURE OF AI ASSISTANTS!")
    print("="*60)
    print("\nStarting ULTRON...\n")

    ultron = JarvisWithBrain()
    try:
        ultron.start()
    except KeyboardInterrupt:
        print("\n[ULTRON] Shutting down...")
        ultron.stop()
    except Exception as e:
        print(f"\n[ULTRON] Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        