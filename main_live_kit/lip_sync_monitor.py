import numpy as np
from collections import deque
import time

class LipSyncMonitor:
    def __init__(self, window_size=30, threshold=0.4):
        """
        :param window_size: Number of data points to keep (e.g., 30 points = ~3 seconds at 10Hz)
        :param threshold: The correlation score below which we flag a violation
        """
        self.window_size = window_size
        self.threshold = threshold
        self.lip_aperture_buffer = deque(maxlen=window_size)
        self.audio_energy_buffer = deque(maxlen=window_size)
        self.vad_active = False
        self.suspicion_score = 0.0
        self.last_update_time = time.time()
        
    def update_vad(self, is_speaking: bool):
        self.vad_active = is_speaking

    def add_data(self, aperture: float, volume: float):
        """
        Add new data points from the client.
        :param aperture: Normalized mouth openness (0.0 to 1.0)
        :param volume: Normalized audio volume from client mic (0.0 to 1.0)
        """
        self.lip_aperture_buffer.append(aperture)
        self.audio_energy_buffer.append(volume)
        self.last_update_time = time.time()

    def analyze(self):
        if len(self.lip_aperture_buffer) < 10:
            return {"status": "initializing", "score": 1.0}

        lip_arr = np.array(self.lip_aperture_buffer)
        aud_arr = np.array(self.audio_energy_buffer)
        
        # 1. Basic Rule: Proxy Speaker Detection
        # If VAD is active but lips haven't moved much in the last second (~10 samples)
        if self.vad_active and np.max(lip_arr[-10:]) < 0.015:
            self.suspicion_score += 1.0
            return {
                "status": "violation",
                "type": "proxy_speaker",
                "message": "Speech detected but lips are closed/static."
            }

        # 2. Rhythm Check: Correlation Calculation
        # We calculate the Pearson correlation between lip aperture and audio volume
        correlation = 0.0
        if len(lip_arr) >= self.window_size:
            corr_matrix = np.corrcoef(lip_arr, aud_arr)
            if not np.isnan(corr_matrix).any():
                correlation = corr_matrix[0, 1]

            # If we are speaking, the correlation should be high
            if self.vad_active:
                if correlation < self.threshold:
                    self.suspicion_score += 1.0
                    return {
                        "status": "violation",
                        "type": "poor_sync",
                        "message": f"Mismatched rhythm. Correlation: {correlation:.2f}"
                    }
                else:
                    self.suspicion_score = max(0.0, self.suspicion_score - 0.5)

        # 3. Silent Mouthing Detection
        # If lips are moving a lot but VAD is silent
        if not self.vad_active and np.ptp(lip_arr[-10:]) > 0.015:
            self.suspicion_score += 0.5
            return {
                "status": "violation",
                "type": "silent_mouthing",
                "message": "Lip movement detected during silence."
            }

        return {"status": "ok", "score": correlation}

    def get_suspicion_level(self):
        """Returns 0 (Safe) to 10 (Definite Cheating)"""
        return min(10.0, self.suspicion_score)