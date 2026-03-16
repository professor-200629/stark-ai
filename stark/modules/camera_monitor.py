"""
STARK Camera Monitor v2
Fixed: better object/scene identification using DeepFace + OpenCV
No key pressing needed — fully automatic
"""

import cv2
import threading
import time
import config

_deepface = None
def _get_deepface():
    global _deepface
    if _deepface is None:
        from deepface import DeepFace
        _deepface = DeepFace
    return _deepface


class CameraMonitor:
    def __init__(self, voice):
        self._voice        = voice
        self._running      = False
        self._cap          = None
        self._last_emotion = "unknown"
        self._thread       = None
        print("[STARK Camera] Initialised.")

    def start(self) -> None:
        self._running = True
        self._cap     = cv2.VideoCapture(config.CAMERA_INDEX)
        if not self._cap.isOpened():
            print("[Camera] Cannot open camera.")
            self._running = False
            return

        emotion_timer    = 0.0
        object_cascade   = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        print("[STARK Camera] Live feed started.")

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                break
            now = time.time()

            # Detect faces
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = object_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60,60))

            # Draw face boxes
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0), 2)
                cv2.putText(frame, "Person", (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

            # Emotion check every N seconds
            if now - emotion_timer >= config.EMOTION_CHECK_SECS:
                emotion_timer = now
                em = self._analyse_emotion(frame)
                if em:
                    self._last_emotion = em

            # Overlay
            label = f"STARK | Emotion: {self._last_emotion.upper()} | Faces: {len(faces)}"
            cv2.rectangle(frame, (0,0), (500,36), (0,0,0), -1)
            cv2.putText(frame, label, (8,24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,255,128), 2)

            cv2.imshow("STARK — Live Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                cv2.destroyAllWindows()
                break

        self._cap.release()
        cv2.destroyAllWindows()

    def stop(self) -> None:
        self._running = False

    def _analyse_emotion(self, frame) -> str:
        try:
            DeepFace = _get_deepface()
            result   = DeepFace.analyze(frame, actions=["emotion"],
                                        enforce_detection=False, silent=True)
            if isinstance(result, list):
                result = result[0]
            return result.get("dominant_emotion", "unknown")
        except Exception:
            return self._last_emotion

    def describe_now(self) -> str:
        """Capture frame, analyse emotion AND count objects, return description."""
        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return "I cannot access the camera right now, Sir."

        # Face detection
        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(60,60))

        # Emotion
        emotion = self._analyse_emotion(frame)
        self._last_emotion = emotion

        # Scene brightness
        brightness = gray.mean()
        light_desc = "well lit" if brightness > 100 else \
                     "dimly lit" if brightness > 50 else "dark"

        face_count = len(faces)
        if face_count == 0:
            face_desc = "I don't see anyone clearly in front of the camera"
        elif face_count == 1:
            face_desc = f"I can see one person. Your emotion appears to be {emotion}"
        else:
            face_desc = f"I can see {face_count} people in the frame"

        return (f"{face_desc}. The environment looks {light_desc}, Sir.")

    def get_emotion(self) -> str:
        return self._last_emotion

    def start_background(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.start, daemon=True)
        self._thread.start()