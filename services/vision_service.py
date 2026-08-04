# services/vision_service.py — Vision service layer
try:
    from screen_vision import ScreenVision
except Exception:
    ScreenVision = None


class VisionService:
    """Service layer for vision — wraps the screen vision module."""

    def __init__(self):
        self.vision = None
        if ScreenVision is not None:
            try:
                self.vision = ScreenVision()
            except Exception as e:
                print(f"[VISION SERVICE] Vision init failed: {e}")

    def capture_screen(self):
        """Capture the current screen and return the image path."""
        if self.vision is not None:
            try:
                return self.vision.capture_screen()
            except Exception as e:
                return f"Vision error: {str(e)}"
        return "Vision service is not available in this environment."

    def extract_text(self, image_path):
        """Extract text from an image file."""
        if self.vision is not None:
            try:
                return self.vision.extract_text(image_path)
            except Exception as e:
                return f"Vision error: {str(e)}"
        return "Vision service is not available in this environment."

    def analyze_screen(self, _=None):
        """Capture the screen and analyze its contents."""
        if self.vision is not None:
            try:
                return self.vision.analyze_screen()
            except Exception as e:
                return f"Vision error: {str(e)}"
        return "Vision service is not available in this environment."