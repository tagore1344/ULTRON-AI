# face_id_advanced.py — PROPER FACE-EMBEDDING BASED VERIFICATION
#
# This module uses face_recognition (dlib) to compute 128-d face embeddings
# and compare them with cosine similarity. If the face_recognition library
# is unavailable, it FALLS BACK to a histogram comparison which is clearly
# labeled as NOT a real security measure (see docs and verify_face()).
import cv2
import pickle
import os
import numpy as np

try:
    import face_recognition
    FACE_RECOGNITION_OK = True
except Exception:
    face_recognition = None
    FACE_RECOGNITION_OK = False


class AdvancedFaceID:
    def __init__(self):
        self.is_enrolled = False
        self.face_model_path = "face_model.pkl"
        self._load_model()

    @property
    def using_real_recognition(self):
        """True if face_recognition (dlib embeddings) is available."""
        return FACE_RECOGNITION_OK

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
                        if self.using_real_recognition:
                            print("[FACE] Face embedding model loaded")
                        else:
                            print("[FACE] WARNING: face_recognition unavailable — "
                                  "using histogram fallback (NOT real security)")
                    else:
                        print("[FACE] Face data is empty, please re-enroll")
            except Exception as e:
                print(f"[FACE] Load error: {e}")

    def _extract_embedding(self, frame):
        """Compute a 128-d face embedding from an RGB frame, or None."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb)
        if not face_locations:
            return None
        encodings = face_recognition.face_encodings(rgb, face_locations)
        return encodings[0] if encodings else None

    def _cosine_similarity(self, a, b):
        a = np.array(a, dtype=np.float64).flatten()
        b = np.array(b, dtype=np.float64).flatten()
        if a.size == 0 or b.size == 0:
            return 0.0
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    def enroll_face(self, name="you"):
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

        # Convert to grayscale for the fallback histogram path
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if gray is None or gray.size == 0:
            print("[FACE] Captured image is empty")
            return False

        # If real recognition is available, use the embedding
        if self.using_real_recognition:
            embedding = self._extract_embedding(frame)
            if embedding is None:
                print("[FACE] No face detected in the captured image. Try again.")
                return False
            self.enrolled_face = embedding
            print("[FACE] Face embedding captured")
        else:
            # Fallback: store a resized grayscale image.
            print("[FACE] WARNING: face_recognition unavailable. "
                  "Storing histogram (NOT real security).")
            self.enrolled_face = cv2.resize(gray, (200, 200))

        self.enrolled_name = name
        self.is_enrolled = True

        with open(self.face_model_path, "wb") as f:
            pickle.dump({
                "face": self.enrolled_face,
                "name": self.enrolled_name,
                "using_real_recognition": self.using_real_recognition,
            }, f)

        print(f"[FACE] ✅ Face enrolled for {name}")
        return True

    def verify_face(self):
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
            # REAL FACE RECOGNITION VIA EMBEDDINGS
            if self.using_real_recognition:
                embedded = self._extract_embedding(frame)
                enrolled = np.array(self.enrolled_face, dtype=np.float64).flatten()
                if embedded is None:
                    print("[FACE] No face detected in the verification frame.")
                    return False
                if enrolled.size == 0:
                    print("[FACE] Enrolled embedding is empty (re-enroll with "
                          "face_recognition installed).")
                    return False
                similarity = self._cosine_similarity(embedded, enrolled)
                # Cosine similarity threshold for face embeddings (~0.5-0.6)
                if similarity > 0.55:
                    print(f"[FACE] ✅ Verified! (cosine similarity: {similarity:.2f})")
                    return True
                print(f"[FACE] ❌ Not recognized (cosine similarity: {similarity:.2f})")
                return False

            # FALLBACK (NOT REAL SECURITY) — histogram comparison
            print("[FACE] WARNING: Verification is using histogram fallback, "
                  "which is NOT a real security measure.")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if gray is None or gray.size == 0:
                print("[FACE] Captured image is empty")
                return False
            if self.enrolled_face is None or self.enrolled_face.size == 0:
                print("[FACE] Enrolled face is empty")
                return False

            gray = cv2.resize(gray, (200, 200))
            enrolled_resized = cv2.resize(self.enrolled_face, (200, 200))

            hist1 = cv2.calcHist([enrolled_resized], [0], None, [256], [0, 256])
            hist2 = cv2.calcHist([gray], [0], None, [256], [0, 256])

            cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)

            similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

            if similarity > 0.6:
                print(f"[FACE] ✅ Verified (histogram similarity: {similarity:.2f})")
                return True
            print(f"[FACE] ❌ Not recognized (histogram similarity: {similarity:.2f})")
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