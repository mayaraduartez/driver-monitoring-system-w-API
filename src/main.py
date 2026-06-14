import cv2
import time
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils
from utils.drawing import draw_landmarks_on_image
from detectors.eye_detector import (
    get_eye_aspect_ratio,
    EyeStateTracker,
    PerclosTracker,
    GazeFocusTracker,
    get_safe_gaze_direction
)
from detectors.hand_detector import (
    is_hand_on_mouth,
    is_hand_on_eyes,
    is_hand_on_face,
    HandBehaviorTracker
)
from detectors.mouth_detector import (
    get_mouth_data,
    MouthStateTracker,
    MouthOpenTracker
)
from detectors.alert_manager import DriverAlertManager
import subprocess
from utils.preprocessing import preprocess_frame
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
from config.config import (
    ENABLE_REMOTE_ALERTS,
    REMOTE_ALERT_LEVELS,
    API_COOLDOWN_SECONDS,
    SYNC_INTERVAL_SECONDS
)

from services.remote_alert_service import RemoteAlertService

# Inicializacao 
capture = cv2.VideoCapture(0) # 0 ou o caminho do video 

# carrega o modelo de detecção facial do arquivo face_landmarker.task q foi baixado 
base_options = python.BaseOptions(model_asset_path='models/face_landmarker.task')

# configura as opções do modelo de detecção facial, como o número máximo de faces a serem detectadas e os limiares de confiança para detecção e rastreamento
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    num_faces=2,
    min_face_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
# carrega o modelo de detecção facial usando as opções definidas acima
detector = vision.FaceLandmarker.create_from_options(options)

# Hands
base_options_hands = python.BaseOptions(model_asset_path='models/hand_landmarker.task')

options_hands = vision.HandLandmarkerOptions(
    base_options=base_options_hands,
    num_hands=2
)
hand_detector = vision.HandLandmarker.create_from_options(options_hands)


#Inicializar rastreador de estado do olho
eye_state_tracker = EyeStateTracker(
    smoothing_window=5,
    calibration_frames=60,
    closed_ratio=0.65,
    open_margin=0.04
)

gaze_focus_tracker = GazeFocusTracker(
    window_seconds=10,
    off_road_min_frames=45,
    min_off_road_percent=35,
    increase_rate=0.03,
    decrease_rate=0.005
)

# inicializa a janela de tempo do perclos
perclos_tracker = PerclosTracker(window_seconds=20)

mouth_state_tracker = MouthStateTracker(
    smoothing_window=5,
    calibration_frames=60,
    min_open_threshold=0.30,
    open_margin=0.15,
    close_margin=0.04,
    yawn_min_frames=30
)

mouth_open_tracker = MouthOpenTracker(window_seconds=20)

hand_behavior_tracker = HandBehaviorTracker(
    increase_rate=0.04,
    decrease_rate=0.005,
    missing_tolerance_frames=10
)

alert_manager = DriverAlertManager()

remote_alert_service = RemoteAlertService()

last_api_alert_time = 0
last_sync_time = 0


def emitir_alerta_sonoro(level):
    sons = {
        "ATENCAO": "sounds/alert.mp3",
        "ALERTA_SONOLENCIA": "sounds/alerta.mp3",
        "ALERTA_DISTRACAO": "sounds/alerta.mp3",
        "CRITICO": "sounds/alerta_critico.mp3",
    }

    caminho_som = sons.get(level, "/System/Library/Sounds/Ping.aiff")

    subprocess.Popen(["afplay", caminho_som])

face_lost_frames = 0
FACE_LOST_RESET_FRAMES = 30
last_sound_time = 0
SOUND_COOLDOWN_SECONDS = 3

# loop principal: lê os frames da câmera, processa as detecções faciais e de mãos, e exibe os resultados na tela
while True:
    # Lê um frame da câmera
    success, frame = capture.read()
    if not success:
        break
    
    frame = cv2.flip(frame, 1)  # Espelhar o feed da câmera
    frame, frame_metrics, filters_used = preprocess_frame(frame)

    # converte o frame de BGR (formato padrão do OpenCV) para RGB (formato esperado pelo MediaPipe)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    # realiza a detecção facial e de mãos usando os modelos carregados, e armazena os resultados em detection_result e hand_result
    detection_result = detector.detect(mp_image)
    hand_result = hand_detector.detect(mp_image)

    # tamanho do frame para calcular as posições relativas das landmarks
    frame_h, frame_w, _ = frame.shape

    # desenha as landmarks faciais e de mãos na imagem usando a função draw_landmarks_on_image, e armazena a imagem anotada em annotated_image
    annotated_image = draw_landmarks_on_image(mp_image.numpy_view(), detection_result)

    # maos
    if hand_result.hand_landmarks:
        for hand_landmarks in hand_result.hand_landmarks:
            drawing_utils.draw_landmarks(
                annotated_image,
                hand_landmarks,
                vision.HandLandmarksConnections.HAND_CONNECTIONS,
                drawing_utils.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=2),
                drawing_utils.DrawingSpec(color=(255,255,255), thickness=2)
            )

    # lógica 
    limiar = 0.5

    if detection_result.face_landmarks:
        face_lost_frames = 0
        for face_landmarks in detection_result.face_landmarks:

            mouth_ratio, mouth_x, mouth_y = get_mouth_data(face_landmarks)
            mouth_state = mouth_state_tracker.update(mouth_ratio)

            mouth_open_data = mouth_open_tracker.update(
                mouth_state["state_numeric"]
            )

            mouth_confidence = mouth_state["confidence"]

            mao_na_boca = is_hand_on_mouth(
                hand_result.hand_landmarks,
                mouth_x,
                mouth_y,
                threshold=0.08,
                min_points_near=2
            )
            
            #Atualizar estado do olho com EAR
            # Primeiro calcula olho
            # 1. Calcula olho
            ear_right, ear_left, ear_average = get_eye_aspect_ratio(face_landmarks)
            eye_state = eye_state_tracker.update(ear_average)

            # 2. Calcula centro dos olhos
            left_eye_x = (
                face_landmarks[362].x +
                face_landmarks[263].x
            ) / 2

            left_eye_y = (
                face_landmarks[386].y +
                face_landmarks[374].y
            ) / 2

            right_eye_x = (
                face_landmarks[33].x +
                face_landmarks[133].x
            ) / 2

            right_eye_y = (
                face_landmarks[159].y +
                face_landmarks[145].y
            ) / 2

            # 3. Detecta mão nos olhos
            mao_nos_olhos = is_hand_on_eyes(
                hand_result.hand_landmarks,
                left_eye_x,
                left_eye_y,
                right_eye_x,
                right_eye_y,
                threshold=0.08,
                min_points_near=2
            )

            mao_no_rosto = is_hand_on_face(
                hand_result.hand_landmarks,
                face_landmarks,
                threshold=0.08,
                min_points_near=2
            )

            # 4. Atualiza comportamento das mãos
            hand_behavior_data = hand_behavior_tracker.update(
                hand_on_mouth=mao_na_boca,
                hand_on_eyes=mao_nos_olhos,
                hand_on_face=mao_no_rosto
            )

            mouth_occlusion_confidence = hand_behavior_data["mouth_occlusion_confidence"]
            eye_occlusion_confidence = hand_behavior_data["eye_occlusion_confidence"]
            face_occlusion_confidence = hand_behavior_data["face_occlusion_confidence"]

            # Só calcula direção do olhar se o olho estiver aberto
            direcao = get_safe_gaze_direction(face_landmarks, eye_state)

            gaze_focus_data = gaze_focus_tracker.update(
                direcao,
                eye_state["state"]
            )

            perclos_data = perclos_tracker.update(eye_state["state_numeric"])
            closed_confidence = eye_state["confidence"]

            alert_data = alert_manager.update(
                eye_closed_confidence=closed_confidence,
                perclos=perclos_data["perclos"],
                mouth_yawn_confidence=mouth_confidence,
                mouth_occlusion_confidence=mouth_occlusion_confidence,
                eye_occlusion_confidence=eye_occlusion_confidence,
                gaze_confidence=gaze_focus_data["confidence"],
                is_phone_like_gaze=gaze_focus_data["is_phone_like_gaze"],
                hand_on_mouth=mao_na_boca,
                face_occlusion_confidence=face_occlusion_confidence
            )


            now = time.time()

            # Envio remoto para API
            if (
                ENABLE_REMOTE_ALERTS
                and alert_data["level"] in REMOTE_ALERT_LEVELS
                and now - last_api_alert_time > API_COOLDOWN_SECONDS
            ):
                remote_alert_service.queue_alert(alert_data)
                last_api_alert_time = now

            # Sincroniza fila offline
            if (
                ENABLE_REMOTE_ALERTS
                and now - last_sync_time > SYNC_INTERVAL_SECONDS
            ):
                remote_alert_service.sync_pending_alerts()
                last_sync_time = now

            # Alerta sonoro
            if alert_data["level"] in ["ALERTA_SONOLENCIA", "ALERTA_DISTRACAO", "CRITICO"]:
                if now - last_sound_time > SOUND_COOLDOWN_SECONDS:
                    emitir_alerta_sonoro(alert_data["level"])
                    last_sound_time = now

            # exibe a direção do olhar e se a mão está na boca na imagem anotada usando a função cv2.putText, que desenha texto na imagem. A direção do olhar é exibida em azul, enquanto a indicação de bocejo com mão é exibida em vermelho.
            cv2.putText(annotated_image, direcao,
                        (50, 100),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (255, 0, 0),
                        2)
            
            # Exibe estado do olho e EAR suavizado
            eye_color = (0, 255, 0) if eye_state['state'] == 'EYE_OPEN' else (0, 0, 255)
            cv2.putText(
                annotated_image,
                f"Olho: {eye_state['state']} | EAR: {eye_state['ear_smoothed']:.3f} | TH: {eye_state['threshold']:.3f}",
                (50, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                eye_color,
                2
            )

            cv2.putText(
                annotated_image,
                f"PERCLOS: {perclos_data['perclos']:.1f}% | Fechados: {perclos_data['closed_frames']}/{perclos_data['total_frames']}",
                (50, 190),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )

            cv2.putText(
                annotated_image,
                f"Conf olho fechado: {closed_confidence:.2f}",
                (50, 220),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 0),
                2
            )
            cv2.putText(
                annotated_image,
                f"Boca: {mouth_state['state']} | MAR: {mouth_state['mar_smoothed']:.3f} | Base: {mouth_state['closed_mar']:.3f} | TH: {mouth_state['threshold']:.3f}",
                (50, 260),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 150, 0),
                2
            )

            cv2.putText(
                annotated_image,
                f"Boca aberta: {mouth_open_data['mouth_open_percent']:.1f}% | Conf: {mouth_confidence:.2f}",
                (50, 290),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 150, 0),
                2
            )

            cv2.putText(
                annotated_image,
                f"Fora da via: {gaze_focus_data['off_road_percent']:.1f}% | Conf: {gaze_focus_data['confidence']:.2f}",
                (50, 330),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 165, 255),
                2
            )

            alert_color = (0, 255, 0)

            if alert_data["level"] == "ATENCAO":
                alert_color = (0, 255, 255)
            elif alert_data["level"] in ["ALERTA_SONOLENCIA", "ALERTA_DISTRACAO"]:
                alert_color = (0, 165, 255)
            elif alert_data["level"] == "CRITICO":
                alert_color = (0, 0, 255)

            cv2.putText(
                annotated_image,
                f"{alert_data['level']} | Sono: {alert_data['sleepiness_score']:.2f} | Distracao: {alert_data['distraction_score']:.2f}",
                (50, 370),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                alert_color,
                2
            )
            if mao_nos_olhos:
                cv2.putText(
                    annotated_image,
                    "Mao nos olhos",
                    (50, 410),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2
                )

            if mao_no_rosto:
                cv2.putText(
                    annotated_image,
                    "Mao no rosto",
                    (50, 440),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2
                )

            cv2.putText(
                annotated_image,
                
                f"Preproc: {', '.join(filters_used) if filters_used else 'nenhum'}",
                (50, 500),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2
            )

            if mao_na_boca:
                cv2.putText(annotated_image, "Mao na boca",
                            (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,
                            (0, 0, 255),
                            2)
    else:
        # Quando face não é detectada, resetar o rastreador de estado
        face_lost_frames += 1

        if face_lost_frames > FACE_LOST_RESET_FRAMES:
            eye_state_tracker.reset()
            perclos_tracker.reset()
            mouth_state_tracker.reset()
            mouth_open_tracker.reset()
            gaze_focus_tracker.reset()
            hand_behavior_tracker.reset()
        

   
    cv2.imshow('Annotated Image', cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))

    if cv2.waitKey(1) & 0xFF == 27:
        break

capture.release()
cv2.destroyAllWindows()