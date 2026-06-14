class DriverAlertManager:
    def __init__(
        self,
        sleepiness_alert_threshold=0.75,
        distraction_alert_threshold=0.75,
        critical_sleepiness_threshold=0.70,
        critical_distraction_threshold=0.60,
        attention_threshold=0.50
    ):
        self.sleepiness_alert_threshold = sleepiness_alert_threshold
        self.distraction_alert_threshold = distraction_alert_threshold
        self.critical_sleepiness_threshold = critical_sleepiness_threshold
        self.critical_distraction_threshold = critical_distraction_threshold
        self.attention_threshold = attention_threshold

    def update(
        self,
        eye_closed_confidence,
        perclos,
        mouth_yawn_confidence,
        mouth_occlusion_confidence,
        eye_occlusion_confidence,
        face_occlusion_confidence,
        gaze_confidence,
        is_phone_like_gaze,
        hand_on_mouth
    ):
        perclos_confidence = min(perclos / 40.0, 1.0)

        phone_like_confidence = 1.0 if is_phone_like_gaze else 0.0
        hand_confidence = 1.0 if hand_on_mouth else 0.0

        sleepiness_score = (
            eye_closed_confidence * 0.25 +
            perclos_confidence * 0.25 +
            mouth_yawn_confidence * 0.20 +
            mouth_occlusion_confidence * 0.15 +
            eye_occlusion_confidence * 0.15 +
            face_occlusion_confidence * 0.08
        )

        distraction_score = (
            gaze_confidence * 0.65 +
            phone_like_confidence * 0.25 +
            hand_confidence * 0.10 +
            face_occlusion_confidence * 0.05
        )

        covered_yawn_score = (
            mouth_yawn_confidence * 0.60 +
            mouth_occlusion_confidence * 0.40
        )

        if covered_yawn_score >= 0.70:
            sleepiness_score = max(sleepiness_score, 0.80)

        hand_occlusion_score = max(
            mouth_occlusion_confidence,
            eye_occlusion_confidence,
            face_occlusion_confidence
        )

        if hand_occlusion_score >= 0.80:
            sleepiness_score = max(sleepiness_score, 0.65)

        if eye_occlusion_confidence >= 0.80:
            sleepiness_score = max(sleepiness_score, 0.65)
        
        if face_occlusion_confidence >= 0.85:
            sleepiness_score = max(sleepiness_score, 0.60)

        if (
            sleepiness_score >= self.critical_sleepiness_threshold
            and distraction_score >= self.critical_distraction_threshold
        ):
            level = "CRITICO"
            message = "Sonolencia e distracao detectadas"

        elif sleepiness_score >= self.sleepiness_alert_threshold:
            level = "ALERTA_SONOLENCIA"
            message = "Sinais de sonolencia detectados"

        elif distraction_score >= self.distraction_alert_threshold:
            level = "ALERTA_DISTRACAO"
            message = "Sinais de distracao detectados"

        elif (
            sleepiness_score >= self.attention_threshold
            or distraction_score >= self.attention_threshold
        ):
            level = "ATENCAO"
            message = "Sinais leves detectados"

        else:
            level = "NORMAL"
            message = "Conducao normal"

        return {
            "level": level,
            "message": message,
            "sleepiness_score": sleepiness_score,
            "distraction_score": distraction_score,
            "perclos_confidence": perclos_confidence,
            "phone_like_confidence": phone_like_confidence,
            "hand_confidence": hand_confidence,
            "mouth_occlusion_confidence": mouth_occlusion_confidence,
            "eye_occlusion_confidence": eye_occlusion_confidence,
            "hand_occlusion_score": hand_occlusion_score,
            "covered_yawn_score": covered_yawn_score,
            "face_occlusion_confidence": face_occlusion_confidence
        }