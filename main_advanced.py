# main_advanced.py — Run Advanced Jarvis with AI Brain
import sys
import os
import time
from assistant_with_brain import JarvisWithBrain

if __name__ == "__main__":
    print("\n" + "="*60)
    print("   🧠 JARVIS — Advanced AI Brain Edition")
    print("   HI TAGORE SIR, WELCOME TO THE FUTURE OF AI ASSISTANTS!")
    print("="*60)
    print("\nStarting Jarvis...\n")

    jarvis = JarvisWithBrain()
    try:
        jarvis.start()
    except KeyboardInterrupt:
        print("\n[JARVIS] Shutting down...")
        jarvis.stop()
    except Exception as e:
        print(f"\n[JARVIS] Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        