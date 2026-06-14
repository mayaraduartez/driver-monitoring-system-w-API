from utils.math_utils import euclidean_distance
from collections import deque
import time

# Calcula se o olho está aberto ou fechado usando EAR.
# Calcula para onde a pessoa está olhando: esquerda, direita ou frente.
# Calcula o valor eAR dos dois olhos

class EyeStateTracker:
    def __init__(
        self,
        smoothing_window=5, # quantos frames usados pra suavizar o EAR
        calibration_frames=60,# quantos frames usados pra calibrar o olho aberto
        closed_ratio=0.65, #percentual do EAR aberto que será considerado limite para olho fechado
        open_margin=0.03 #margem para evitar oscilação entre aberto e fechado (histerese)
    ):
        self.smoothing_window = smoothing_window
        self.calibration_frames = calibration_frames
        self.closed_ratio = closed_ratio
        self.open_margin = open_margin

        self.ear_history = [] # lista com ultimos valores de EAR
        self.open_ear_samples = [] #lista usada somente durante a calibraçao inicial

        self.open_ear = None # ear medio do olho aberto
        self.close_threshold = None
        self.open_threshold = None

        self.current_state = "CALIBRATING" #estado inicial

        self.closed_confidence = TemporalConfidence(
            increase_rate=0.08,
            decrease_rate=0.04
        )

    def update(self, ear_average):
        self.ear_history.append(ear_average)

        if len(self.ear_history) > self.smoothing_window:
            self.ear_history.pop(0)

        ear_smoothed = sum(self.ear_history) / len(self.ear_history)

        # calibração inicial assumindo que o usuário começa com olho aberto
        if len(self.open_ear_samples) < self.calibration_frames:
            self.open_ear_samples.append(ear_smoothed)

            self.open_ear = sum(self.open_ear_samples) / len(self.open_ear_samples) # calcula a media do olho aberto
            self.close_threshold = self.open_ear * self.closed_ratio # calcula limite do olho fechado
            self.open_threshold = self.close_threshold + self.open_margin # calcula o limite para voltar a considerar o olho aberto

            self.current_state = "CALIBRATING"

            return {
                "ear_raw": ear_average,
                "ear_smoothed": ear_smoothed,
                "state": self.current_state,
                "state_numeric": 1,
                "threshold": self.close_threshold,
                "open_ear": self.open_ear,
                "confidence": 0.0

            }

        # atualiza lentamente o EAR aberto quando o olho está claramente aberto
        if ear_smoothed > self.open_threshold:
            self.open_ear = (self.open_ear * 0.98) + (ear_smoothed * 0.02) # atualiza lentamente o valor de EAR aberto, usa 98% do antigo ee 4% do nov, para não mudar bruscamente
            #recalcula os thresholds
            self.close_threshold = self.open_ear * self.closed_ratio
            self.open_threshold = self.close_threshold + self.open_margin

        # histerese: evita ficar alternando aberto/fechado
        if self.current_state != "EYE_CLOSED":
            if ear_smoothed < self.close_threshold:
                self.current_state = "EYE_CLOSED"
            else:
                self.current_state = "EYE_OPEN"
        else:
            if ear_smoothed > self.open_threshold:
                self.current_state = "EYE_OPEN"

        confidence = self.closed_confidence.update(
            self.current_state == "EYE_CLOSED"
        )

        return {
            "ear_raw": ear_average, # ear original
            "ear_smoothed": ear_smoothed, # ear suavizado
            "state": self.current_state, # estado
            "state_numeric": 1 if self.current_state == "EYE_OPEN" else 0, # estado em 0 ou 1
            "threshold": self.close_threshold, # threshold de fechamento
            "open_ear": self.open_ear, # ear medio estimado para olho aberto 
            "confidence": confidence
        }

    # usado quando perde o rosto
    def reset(self):
        self.ear_history = []
        self.open_ear_samples = []
        self.open_ear = None
        self.close_threshold = None
        self.open_threshold = None
        self.current_state = "CALIBRATING"
        self.closed_confidence.reset()

class PerclosTracker:
    def __init__(self, window_seconds=20):
        self.window_seconds = window_seconds
        self.frames = deque()

    def update(self, eye_state_numeric):
        now = time.time()

        # Guarda o frame atual
        # 1 = olho aberto
        # 0 = olho fechado
        self.frames.append({
            "time": now,
            "closed": 1 if eye_state_numeric == 0 else 0
        })

        # Remove frames fora da janela de tempo
        while self.frames and now - self.frames[0]["time"] > self.window_seconds:
            self.frames.popleft()

        total_frames = len(self.frames)

        if total_frames == 0:
            return {
                "perclos": 0,
                "closed_frames": 0,
                "total_frames": 0
            }

        closed_frames = sum(frame["closed"] for frame in self.frames)

        perclos = (closed_frames / total_frames) * 100

        return {
            "perclos": perclos,
            "closed_frames": closed_frames,
            "total_frames": total_frames
        }

    def reset(self):
        self.frames.clear()

class TemporalConfidence:
    def __init__(
        self,
        increase_rate=0.08,
        decrease_rate=0.04,
        min_confidence=0.0,
        max_confidence=1.0
    ):
        self.increase_rate = increase_rate
        self.decrease_rate = decrease_rate
        self.min_confidence = min_confidence
        self.max_confidence = max_confidence
        self.confidence = 0.0

    def update(self, evidence_present):
        """
        evidence_present:
            True  = evidência presente
            False = evidência ausente
        """

        if evidence_present:
            self.confidence += self.increase_rate
        else:
            self.confidence -= self.decrease_rate

        self.confidence = max(
            self.min_confidence,
            min(self.confidence, self.max_confidence)
        )

        return self.confidence

    def reset(self):
        self.confidence = 0.0

class GazeFocusTracker:
    def __init__(
        self,
        window_seconds=10,
        off_road_min_frames=30,
        min_off_road_percent=25,
        increase_rate=0.03,
        decrease_rate=0.005
    ):
        self.window_seconds = window_seconds
        self.off_road_min_frames = off_road_min_frames
        self.min_off_road_percent = min_off_road_percent

        self.frames = deque()
        self.consecutive_off_road_frames = 0

        self.confidence_tracker = TemporalConfidence(
            increase_rate=increase_rate,
            decrease_rate=decrease_rate
        )

    def update(self, gaze_direction, eye_state):
        now = time.time()

        valid_gaze = eye_state == "EYE_OPEN"

        is_off_road = (
            valid_gaze and
            gaze_direction in [
                "Olhando ESQUERDA",
                "Olhando DIREITA",
                "Olhando BAIXO"
            ]
        )

        is_phone_like_gaze = (
            valid_gaze and
            gaze_direction == "Olhando BAIXO"
        )

        self.frames.append({
            "time": now,
            "valid": 1 if valid_gaze else 0,
            "off_road": 1 if is_off_road else 0
        })

        while self.frames and now - self.frames[0]["time"] > self.window_seconds:
            self.frames.popleft()

        valid_frames = sum(frame["valid"] for frame in self.frames)
        off_road_frames = sum(frame["off_road"] for frame in self.frames)

        if valid_frames == 0:
            off_road_percent = 0
        else:
            off_road_percent = (off_road_frames / valid_frames) * 100

        if is_off_road:
            self.consecutive_off_road_frames += 1
        else:
            self.consecutive_off_road_frames = 0

        is_distraction_evidence = (
            self.consecutive_off_road_frames >= self.off_road_min_frames
            and off_road_percent >= self.min_off_road_percent
        )

        confidence = self.confidence_tracker.update(is_distraction_evidence)

        return {
            "valid_gaze": valid_gaze,
            "is_off_road": is_off_road,
            "is_phone_like_gaze": is_phone_like_gaze,
            "off_road_percent": off_road_percent,
            "off_road_frames": off_road_frames,
            "valid_frames": valid_frames,
            "consecutive_off_road_frames": self.consecutive_off_road_frames,
            "is_distraction_evidence": is_distraction_evidence,
            "confidence": confidence
            
        }

    def reset(self):
        self.frames.clear()
        self.consecutive_off_road_frames = 0
        self.confidence_tracker.reset()

def get_gaze_direction(face_landmarks):
    right_inner = face_landmarks[33]
    right_outer = face_landmarks[133]
    left_inner  = face_landmarks[362]
    left_outer  = face_landmarks[263]

    right_top = face_landmarks[159]
    right_bottom = face_landmarks[145]

    left_top = face_landmarks[386]
    left_bottom = face_landmarks[374]

    right_iris = face_landmarks[468]
    left_iris  = face_landmarks[473]

    def get_horizontal_ratio(inner, iris, outer):
        horizontal = euclidean_distance(inner, outer)

        if horizontal == 0:
            return 0.5

        return euclidean_distance(inner, iris) / horizontal

    def get_vertical_ratio(top, iris, bottom):
        vertical = euclidean_distance(top, bottom)

        if vertical == 0:
            return 0.5

        return euclidean_distance(top, iris) / vertical

    right_h = get_horizontal_ratio(right_inner, right_iris, right_outer)
    left_h = get_horizontal_ratio(left_inner, left_iris, left_outer)

    right_v = get_vertical_ratio(right_top, right_iris, right_bottom)
    left_v = get_vertical_ratio(left_top, left_iris, left_bottom)

    gaze_h = (right_h + left_h) / 2
    gaze_v = (right_v + left_v) / 2

    if gaze_v > 0.65:
        return "Olhando BAIXO"

    if gaze_v < 0.35:
        return "Olhando CIMA"

    if gaze_h < 0.4:
        return "Olhando ESQUERDA"

    if gaze_h > 0.6:
        return "Olhando DIREITA"

    return "Olhando FRENTE"

# calcula o EAR dos dois olhos 
def get_eye_aspect_ratio(face_landmarks):
    right = [33, 160, 158, 133, 153, 144]
    left  = [362, 385, 387, 263, 373, 380]

    def calc(points):
        p1, p2, p3, p4, p5, p6 = [face_landmarks[i] for i in points]

        vertical_1 = euclidean_distance(p2, p6)
        vertical_2 = euclidean_distance(p3, p5)
        horizontal = euclidean_distance(p1, p4)

        if horizontal == 0:
            return 0

        return (vertical_1 + vertical_2) / (2.0 * horizontal)

    ear_right = calc(right)
    ear_left = calc(left)

    return ear_right, ear_left, (ear_right + ear_left) / 2

def get_safe_gaze_direction(face_landmarks, eye_state):
    if eye_state["state"] == "EYE_CLOSED":
        return "Olho fechado"

    if eye_state["state"] == "CALIBRATING":
        return "Calibrando olho"

    return get_gaze_direction(face_landmarks)
