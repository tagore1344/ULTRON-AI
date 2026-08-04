# face_id_advanced.py — COMPLETELY FIXED
import pickle
import os

try:
    import cv2
except Exception:
    cv2 = None

try:
    import numpy as np
except Exception:
    np = None

class AdvancedFaceID:
    def __init__(self):
        self.is_enrolled = False
        self.face_model_path = "face_model.pkl"
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.face_model_path):
            try:
                with open(self.face_model_path, "rb") as f:
                    data = pickle.load(f)
                    if isinstance(data, dict):
                        self.enrolled_face = data.get("face")
                        self.enrolled_name = data.get("name", "you")
                    else:
                        self.enrolled_face = data
                        self.enrolled_name = "you"
                    
                    if self.enrolled_face is not None and len(self.enrolled_face) > 0:
                        self.is_enrolled = True
                        print("[FACE] Face model loaded")
                    else:
                        print("[FACE] Face data is empty, please re-enroll")
            except Exception as e:
                print(f"[FACE] Load error: {e}")

    def enroll_face(self, name="you"):
        if cv2 is None:
            print("[FACE] OpenCV is unavailable in this environment")
            return False

        print("[FACE] Look at the camera.")
        video_capture = cv2.VideoCapture(0)
        if not video_capture.isOpened():
            print("[FACE] No camera detected")
            return False
            
        ret, frame = video_capture.read()
        video_capture.release()
        
        if not ret:
            print("[FACE] Could not capture image")
            return False

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Check if image is valid
        if gray is None or gray.size == 0:
            print("[FACE] Captured image is empty")
            return False
            
        # Save face data
        self.enrolled_face = gray
        self.enrolled_name = name
        self.is_enrolled = True
        
        with open(self.face_model_path, "wb") as f:
            pickle.dump({
                "face": self.enrolled_face,
                "name": self.enrolled_name
            }, f)
        
        print(f"[FACE] ✅ Face enrolled for {name}")
        return True

    def verify_face(self):
        if cv2 is None:
            print("[FACE] OpenCV is unavailable in this environment")
            return True

        if not self.is_enrolled or self.enrolled_face is None:
            print("[FACE] No enrolled face. Skipping verification.")
            return True

        video_capture = cv2.VideoCapture(0)
        if not video_capture.isOpened():
            print("[FACE] No camera detected")
            return False
            
        ret, frame = video_capture.read()
        video_capture.release()
        
        if not ret:
            print("[FACE] Could not capture image")
            return False

        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if gray is None or gray.size == 0:
                print("[FACE] Captured image is empty")
                return False
                
            # Ensure both images are valid
            if self.enrolled_face is None or self.enrolled_face.size == 0:
                print("[FACE] Enrolled face is empty")
                return False
                
            # Resize both to same size
            gray = cv2.resize(gray, (200, 200))
            enrolled_resized = cv2.resize(self.enrolled_face, (200, 200))
            
            # Calculate histogram
            hist1 = cv2.calcHist([enrolled_resized], [0], None, [256], [0, 256])
            hist2 = cv2.calcHist([gray], [0], None, [256], [0, 256])
            
            # Normalize
            cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)
            
            # Compare
            similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            
            if similarity > 0.6:
                print(f"[FACE] ✅ Verified! (similarity: {similarity:.2f})")
                return True
            else:
                print(f"[FACE] ❌ Not recognized (similarity: {similarity:.2f})")
                return False
                
        except Exception as e:
            print(f"[FACE] Verification error: {e}")
            return False

    def delete_face(self):
        if os.path.exists(self.face_model_path):
            os.remove(self.face_model_path)
        self.is_enrolled = False
        self.enrolled_face = None
        print("[FACE] Face data deleted")