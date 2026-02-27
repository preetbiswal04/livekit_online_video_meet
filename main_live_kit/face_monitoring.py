import cv2
import numpy as np
import base64
import os

class FaceMonitor:
    def __init__(self):
        # Load multiple classifiers for better robustness
        self.frontal_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
        
        if self.frontal_cascade.empty() or self.profile_cascade.empty():
            print("--- [WARNING] One or more Haar Cascade XML files failed to load.")

    def analyze_frame(self, frame):
        """
        Analyzes a single frame for face presence.
        Returns a dictionary with 'violation' (True if no face or >1 face) and 'count'.
        """
        if frame is None:
            return {"violation": True, "error": "No frame provided", "count": 0}

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Histogram equalization to improve contrast
            gray = cv2.equalizeHist(gray)
            
            # Detect frontal faces - tuned for sensitivity
            frontal_faces = self.frontal_cascade.detectMultiScale(
                gray, scaleFactor=1.05, minNeighbors=4, minSize=(40, 40)
            )
            
            # Detect profile faces
            profile_faces = self.profile_cascade.detectMultiScale(
                gray, scaleFactor=1.05, minNeighbors=4, minSize=(40, 40)
            )
            
            # Combine detections (naively to start)
            # We use list(frontal_faces) + list(profile_faces) then perhaps NMS if needed, 
            # but for simple counting, even a basic sum can indicate multiple people.
            total_faces = list(frontal_faces) + list(profile_faces)
            
            # Very basic deduplication: if count > 0, we can refine, 
            # but simple length is usually enough to trigger a violation if > 1.
            count = len(total_faces)
            
            # Violation if no face (0) or multiple faces (>1)
            violation = (count != 1)
            
            message = "Detection successful"
            if count == 0:
                message = "No face detected"
            elif count > 1:
                message = f"Multiple faces detected ({count})"
                
            return {
                "violation": violation,
                "count": count,
                "message": message
            }
        except Exception as e:
            print(f"--- [ERROR] Face Analysis Error: {e}")
            return {"violation": True, "error": str(e), "count": 0}

# Global instance
face_monitor = FaceMonitor()
