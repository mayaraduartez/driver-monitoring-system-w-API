import math


FINGER_POINTS = [4, 8, 12, 16, 20]


def is_hand_on_mouth(
    hand_landmarks_list,
    mouth_x,
    mouth_y,
    threshold=0.08,
    min_points_near=2
):
    if not hand_landmarks_list:
        return False

    for hand_landmarks in hand_landmarks_list:
        points_near = 0

        for index in FINGER_POINTS:
            point = hand_landmarks[index]

            dist = math.sqrt(
                (point.x - mouth_x) ** 2 +
                (point.y - mouth_y) ** 2
            )

            if dist < threshold:
                points_near += 1

        if points_near >= min_points_near:
            return True

    return False

def is_hand_on_eyes(
        
    hand_landmarks_list,
    left_eye_x,
    left_eye_y,
    right_eye_x,
    right_eye_y,
    threshold=0.08,
    min_points_near=2
):
    if not hand_landmarks_list:
        return False

    for hand_landmarks in hand_landmarks_list:
        points_near = 0

        for index in FINGER_POINTS:
            point = hand_landmarks[index]

            dist_left = math.sqrt(
                (point.x - left_eye_x) ** 2 +
                (point.y - left_eye_y) ** 2
            )

            dist_right = math.sqrt(
                (point.x - right_eye_x) ** 2 +
                (point.y - right_eye_y) ** 2
            )

            if dist_left < threshold or dist_right < threshold:
                points_near += 1

        if points_near >= min_points_near:
            return True

    return False
    
def is_hand_on_face(
    hand_landmarks_list,
    face_landmarks,
    threshold=0.08,
    min_points_near=2
):
    if not hand_landmarks_list:
        return False

    # Pontos principais do rosto
    face_points = [
        1,    # nariz
        152,  # queixo
        234,  # bochecha esquerda
        454,  # bochecha direita
        10,   # testa
    ]

    for hand_landmarks in hand_landmarks_list:
        points_near = 0

        for finger_index in FINGER_POINTS:
            finger = hand_landmarks[finger_index]

            for face_index in face_points:
                face_point = face_landmarks[face_index]

                dist = math.sqrt(
                    (finger.x - face_point.x) ** 2 +
                    (finger.y - face_point.y) ** 2
                )

                if dist < threshold:
                    points_near += 1
                    break

        if points_near >= min_points_near:
            return True

    return False

class HandBehaviorTracker:
    def __init__(
        self,
        increase_rate=0.04,
        decrease_rate=0.005,
        missing_tolerance_frames=10,
        mouth_min_frames=15,
        eye_min_frames=15,
        face_min_frames=45
    ):
        self.increase_rate = increase_rate
        self.decrease_rate = decrease_rate
        self.missing_tolerance_frames = missing_tolerance_frames

        self.mouth_min_frames = mouth_min_frames
        self.eye_min_frames = eye_min_frames
        self.face_min_frames = face_min_frames

        self.mouth_occlusion_confidence = 0.0
        self.eye_occlusion_confidence = 0.0
        self.face_occlusion_confidence = 0.0

        self.mouth_missing_frames = 0
        self.eye_missing_frames = 0
        self.face_missing_frames = 0

        self.mouth_consecutive_frames = 0
        self.eye_consecutive_frames = 0
        self.face_consecutive_frames = 0

    def _update_confidence(
        self,
        current_confidence,
        missing_frames,
        evidence_present,
        increase_rate,
        decrease_rate,
        tolerance_frames
    ):
        if evidence_present:
            missing_frames = 0
            current_confidence += increase_rate
        else:
            missing_frames += 1

            if missing_frames > tolerance_frames:
                current_confidence -= decrease_rate

        current_confidence = max(0.0, min(current_confidence, 1.0))

        return current_confidence, missing_frames

    def update(self, hand_on_mouth, hand_on_eyes, hand_on_face):
        if hand_on_mouth:
            self.mouth_consecutive_frames += 1
        else:
            self.mouth_consecutive_frames = 0

        if hand_on_eyes:
            self.eye_consecutive_frames += 1
        else:
            self.eye_consecutive_frames = 0

        if hand_on_face:
            self.face_consecutive_frames += 1
        else:
            self.face_consecutive_frames = 0

        mouth_evidence = self.mouth_consecutive_frames >= self.mouth_min_frames
        eye_evidence = self.eye_consecutive_frames >= self.eye_min_frames
        face_evidence = self.face_consecutive_frames >= self.face_min_frames

        self.mouth_occlusion_confidence, self.mouth_missing_frames = self._update_confidence(
            self.mouth_occlusion_confidence,
            self.mouth_missing_frames,
            mouth_evidence,
            increase_rate=self.increase_rate,
            decrease_rate=self.decrease_rate,
            tolerance_frames=self.missing_tolerance_frames
        )

        self.eye_occlusion_confidence, self.eye_missing_frames = self._update_confidence(
            self.eye_occlusion_confidence,
            self.eye_missing_frames,
            eye_evidence,
            increase_rate=self.increase_rate,
            decrease_rate=self.decrease_rate,
            tolerance_frames=self.missing_tolerance_frames
        )

        self.face_occlusion_confidence, self.face_missing_frames = self._update_confidence(
            self.face_occlusion_confidence,
            self.face_missing_frames,
            face_evidence,
            increase_rate=0.01,
            decrease_rate=0.003,
            tolerance_frames=45
        )

        return {
            "mouth_occlusion_confidence": self.mouth_occlusion_confidence,
            "eye_occlusion_confidence": self.eye_occlusion_confidence,
            "face_occlusion_confidence": self.face_occlusion_confidence,
            "mouth_consecutive_frames": self.mouth_consecutive_frames,
            "eye_consecutive_frames": self.eye_consecutive_frames,
            "face_consecutive_frames": self.face_consecutive_frames,
            "mouth_evidence": mouth_evidence,
            "eye_evidence": eye_evidence,
            "face_evidence": face_evidence
        }

    def reset(self):
        self.mouth_occlusion_confidence = 0.0
        self.eye_occlusion_confidence = 0.0
        self.face_occlusion_confidence = 0.0

        self.mouth_missing_frames = 0
        self.eye_missing_frames = 0
        self.face_missing_frames = 0

        self.mouth_consecutive_frames = 0
        self.eye_consecutive_frames = 0
        self.face_consecutive_frames = 0