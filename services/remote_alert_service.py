import requests
from datetime import datetime

from config.config import (
    ENABLE_REMOTE_ALERTS,
    API_URL,
    API_TOKEN,
    VEICULO_ID,
    MOTORISTA_ID,
    DISPOSITIVO_ID,
    REQUEST_TIMEOUT_SECONDS
)

from services.alert_queue import AlertQueue


class RemoteAlertService:
    def __init__(self):
        self.queue = AlertQueue()

    def build_payload(self, alert_data):
        return {
            "veiculo_id": VEICULO_ID,
            "motorista_id": MOTORISTA_ID,
            "dispositivo_id": DISPOSITIVO_ID,
            "data_hora": datetime.now().isoformat(),

            "level": alert_data.get("level"),
            "message": alert_data.get("message"),

            "sleepiness_score": alert_data.get("sleepiness_score"),
            "distraction_score": alert_data.get("distraction_score"),
            "perclos_confidence": alert_data.get("perclos_confidence"),

            "mouth_occlusion_confidence": alert_data.get("mouth_occlusion_confidence"),
            "eye_occlusion_confidence": alert_data.get("eye_occlusion_confidence"),
            "face_occlusion_confidence": alert_data.get("face_occlusion_confidence"),

            "hand_occlusion_score": alert_data.get("hand_occlusion_score"),
            "covered_yawn_score": alert_data.get("covered_yawn_score"),
            "phone_like_confidence": alert_data.get("phone_like_confidence"),

            "origem": "raspberry_local",
            "possui_imagem": False,
            "possui_video": False
        }

    def queue_alert(self, alert_data):
        if not ENABLE_REMOTE_ALERTS:
            return None

        payload = self.build_payload(alert_data)
        level = payload["level"]

        return self.queue.add_alert(level, payload)

    def send_alert(self, alert_id, payload):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_TOKEN}"
        }

        response = requests.post(
            API_URL,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS
        )

        response.raise_for_status()

        self.queue.mark_as_sent(alert_id)

        return True

    def sync_pending_alerts(self, limit=10):
        if not ENABLE_REMOTE_ALERTS:
            return {
                "sent": 0,
                "failed": 0,
                "pending": self.queue.count_pending()
            }

        pending_alerts = self.queue.get_pending_alerts(limit=limit)

        sent = 0
        failed = 0

        for alert in pending_alerts:
            try:
                self.send_alert(
                    alert_id=alert["id"],
                    payload=alert["payload"]
                )
                sent += 1

            except Exception as error:
                self.queue.mark_as_error(
                    alert_id=alert["id"],
                    error_message=error
                )
                failed += 1

        return {
            "sent": sent,
            "failed": failed,
            "pending": self.queue.count_pending()
        }