from utils.math_utils import euclidean_distance
from collections import deque
import time


class TemporalConfidence:
    def __init__(
        self,
        increase_rate=0.04,
        decrease_rate=0.003,
        min_confidence=0.0,
        max_confidence=1.0,
        missing_tolerance_frames=30
    ):
        self.increase_rate = increase_rate
        self.decrease_rate = decrease_rate
        self.min_confidence = min_confidence
        self.max_confidence = max_confidence
        self.confidence = 0.0
        self.missing_tolerance_frames = missing_tolerance_frames
        self.missing_frames = 0

    def update(self, evidence_present):
        if evidence_present:
            self.missing_frames = 0
            self.confidence += self.increase_rate
        else:
            self.missing_frames += 1

            if self.missing_frames > self.missing_tolerance_frames:
                self.confidence -= self.decrease_rate

        self.confidence = max(
            self.min_confidence,
            min(self.confidence, self.max_confidence)
        )

        return self.confidence

    def reset(self):
        self.confidence = 0.0
        self.missing_frames = 0

class MouthStateTracker:
    def __init__(
        self,
        smoothing_window=5,
        calibration_frames=60,
        min_open_threshold=0.30,
        open_margin=0.15,
        close_margin=0.04,
        yawn_min_frames=30
    ):
        self.smoothing_window = smoothing_window
        self.calibration_frames = calibration_frames
        self.min_open_threshold = min_open_threshold
        self.open_margin = open_margin
        self.close_margin = close_margin
        self.yawn_min_frames = yawn_min_frames

        self.mar_history = []
        self.closed_mar_samples = []

        self.closed_mar = None
        self.open_threshold = None
        self.close_threshold = None

        self.current_state = "CALIBRATING"
        self.consecutive_open_frames = 0

        self.open_confidence = TemporalConfidence(
            increase_rate=0.04,
            decrease_rate=0.002,
            missing_tolerance_frames=30
        )

    def update(self, mar):
        self.mar_history.append(mar)

        if len(self.mar_history) > self.smoothing_window:
            self.mar_history.pop(0)

        mar_smoothed = sum(self.mar_history) / len(self.mar_history)

        if len(self.closed_mar_samples) < self.calibration_frames:
            self.closed_mar_samples.append(mar_smoothed)

            self.closed_mar = (
                sum(self.closed_mar_samples) /
                len(self.closed_mar_samples)
            )

            self.open_threshold = max(
                self.min_open_threshold,
                self.closed_mar + self.open_margin
            )

            self.close_threshold = self.open_threshold - self.close_margin
            self.current_state = "CALIBRATING"

            return {
                "mar_raw": mar,
                "mar_smoothed": mar_smoothed,
                "state": self.current_state,
                "state_numeric": 0,
                "threshold": self.open_threshold,
                "close_threshold": self.close_threshold,
                "closed_mar": self.closed_mar,
                "confidence": 0.0,
                "consecutive_open_frames": 0,
                "is_yawn_evidence": False,
            }

        mouth_open_detected = (
            mar_smoothed > self.open_threshold
        )

        if self.current_state != "MOUTH_OPEN":
            if mouth_open_detected:
                self.current_state = "MOUTH_OPEN"
            else:
                self.current_state = "MOUTH_CLOSED"
        else:
            if mar_smoothed < self.close_threshold:
                self.current_state = "MOUTH_CLOSED"

        if self.current_state == "MOUTH_OPEN":
            self.consecutive_open_frames += 1
        else:
            self.consecutive_open_frames = 0

        is_yawn_evidence = (
            self.consecutive_open_frames >= self.yawn_min_frames
        )

        confidence = self.open_confidence.update(is_yawn_evidence)

        return {
            "mar_raw": mar,
            "mar_smoothed": mar_smoothed,
            "state": self.current_state,
            "state_numeric": 1 if self.current_state == "MOUTH_OPEN" else 0,
            "threshold": self.open_threshold,
            "close_threshold": self.close_threshold,
            "closed_mar": self.closed_mar,
            "confidence": confidence,
            "consecutive_open_frames": self.consecutive_open_frames,
            "is_yawn_evidence": is_yawn_evidence,
        }

    def reset(self):
        self.mar_history = []
        self.closed_mar_samples = []
        self.closed_mar = None
        self.open_threshold = None
        self.close_threshold = None
        self.current_state = "CALIBRATING"
        self.consecutive_open_frames = 0
        self.open_confidence.reset()
        
class MouthOpenTracker:
    def __init__(self, window_seconds=20):
        self.window_seconds = window_seconds
        self.frames = deque()

    def update(self, mouth_state_numeric):
        now = time.time()

        self.frames.append({
            "time": now,
            "open": 1 if mouth_state_numeric == 1 else 0
        })

        while self.frames and now - self.frames[0]["time"] > self.window_seconds:
            self.frames.popleft()

        total_frames = len(self.frames)

        if total_frames == 0:
            return {
                "mouth_open_percent": 0,
                "open_frames": 0,
                "total_frames": 0
            }

        open_frames = sum(frame["open"] for frame in self.frames)

        mouth_open_percent = (open_frames / total_frames) * 100

        return {
            "mouth_open_percent": mouth_open_percent,
            "open_frames": open_frames,
            "total_frames": total_frames
        }

    def reset(self):
        self.frames.clear()


def get_mouth_data(face_landmarks):
    # Landmarks mais usados para boca no MediaPipe FaceMesh
    mouth_left = face_landmarks[61]
    mouth_right = face_landmarks[291]

    top_left = face_landmarks[81]
    bottom_left = face_landmarks[178]

    top_center = face_landmarks[13]
    bottom_center = face_landmarks[14]

    top_right = face_landmarks[311]
    bottom_right = face_landmarks[402]

    vertical_left = euclidean_distance(top_left, bottom_left)
    vertical_center = euclidean_distance(top_center, bottom_center)
    vertical_right = euclidean_distance(top_right, bottom_right)

    horizontal = euclidean_distance(mouth_left, mouth_right)

    if horizontal == 0:
        mar = 0
    else:
        mar = (vertical_left + vertical_center + vertical_right) / (2.0 * horizontal)

    mouth_x = (top_center.x + bottom_center.x) / 2
    mouth_y = (top_center.y + bottom_center.y) / 2

    return mar, mouth_x, mouth_y