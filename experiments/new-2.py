import cv2
import mediapipe as mp
import sys
from collections import deque
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils
from mediapipe.tasks.python.vision import drawing_styles
import numpy as np

# Limiares de MAR (Mouth Aspect Ratio).
MAR_OPEN_THRESHOLD = 0.25       # Limiar minimo de MAR para considerar a boca aberta.
MAR_YAWN_LIKE_THRESHOLD = 0.65  # Limiar de MAR alto usado para classificar abertura tipo bocejo.
SMOOTHING_WINDOW = 7            # Quantidade de frames usados na media movel do MAR.
MIN_YAWN_FRAMES = 15            # Frames consecutivos acima do limiar de bocejo para confirmar evento.
YAWN_BANNER_FRAMES = 15         # Frames que a mensagem de bocejo permanece visivel na tela.
YAWN_COOLDOWN_FRAMES = 15       # Frames de espera apos detectar bocejo para evitar repeticoes.
PLAYBACK_SPEED = 0.6           # Velocidade de reproducao do video (0.25x = 4x mais lento).
# Limiares da posicao horizontal normalizada da iris no olho.
GAZE_LEFT_THRESHOLD = 0.40
GAZE_RIGHT_THRESHOLD = 0.60

# Estilo fino para desenhar conexoes com menor espessura.
_DEFAULT_CONTOUR_STYLE = drawing_styles.get_default_face_mesh_contours_style()
THIN_CONTOUR_STYLE = {
    connection: drawing_utils.DrawingSpec(
        color=spec.color,
        thickness=1,
        circle_radius=spec.circle_radius,
    )
    for connection, spec in _DEFAULT_CONTOUR_STYLE.items()
}

# Baseado no exemplo oficial do MediaPipe Tasks:
# https://colab.research.google.com/github/googlesamples/mediapipe/blob/main/examples/face_landmarker/python/%5BMediaPipe_Python_Tasks%5D_Face_Landmarker.ipynb#scrollTo=s3E6NFV-00Qt
def draw_landmarks_on_image(rgb_image, detection_result):
    # Desenha malha facial, contornos e iris para cada face detectada.
    face_landmarks_list = detection_result.face_landmarks
    annotated_image = np.copy(rgb_image)

    # Percorre todas as faces detectadas para renderizar os pontos.
    for idx in range(len(face_landmarks_list)):
        face_landmarks = face_landmarks_list[idx]

        # Desenha os pontos da malha facial (landmarks) e as conexões dos lábios.
        drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=face_landmarks,
            connections=vision.FaceLandmarksConnections.FACE_LANDMARKS_LIPS,
            landmark_drawing_spec=None,
            connection_drawing_spec=THIN_CONTOUR_STYLE
        )
        """# Desenha a tesselação (triangulação) de toda a malha facial.
        drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=face_landmarks,
            connections=vision.FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION,
            landmark_drawing_spec=None,
            connection_drawing_spec=drawing_styles.get_default_face_mesh_tesselation_style())

        # Desenha apenas os contornos principais do rosto.
        drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=face_landmarks,
            connections=vision.FaceLandmarksConnections.FACE_LANDMARKS_CONTOURS,
            landmark_drawing_spec=None,
            connection_drawing_spec=drawing_styles.get_default_face_mesh_contours_style())"""

        # Desenha a íris esquerda.
        drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=face_landmarks,
            connections=vision.FaceLandmarksConnections.FACE_LANDMARKS_LEFT_IRIS,
            landmark_drawing_spec=None,
            connection_drawing_spec=drawing_styles.get_default_face_mesh_iris_connections_style())

        # Desenha a íris direita.
        drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=face_landmarks,
            connections=vision.FaceLandmarksConnections.FACE_LANDMARKS_RIGHT_IRIS,
            landmark_drawing_spec=None,
            connection_drawing_spec=drawing_styles.get_default_face_mesh_iris_connections_style())

    return annotated_image


def euclidean_distance(p1, p2):
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    return float(np.sqrt((dx * dx) + (dy * dy)))


def calculate_mar(face_landmarks):
    """Calcula MAR da boca usando landmarks de labios superior/inferior e cantos."""
    top_lip = face_landmarks[13]
    bottom_lip = face_landmarks[14]
    left_corner = face_landmarks[78]
    right_corner = face_landmarks[308]

    mouth_open = euclidean_distance(top_lip, bottom_lip)
    mouth_width = euclidean_distance(left_corner, right_corner)

    if mouth_width <= 1e-6:
        return 0.0
    return mouth_open / mouth_width


def draw_mouth_flag(image_bgr, mar_raw, mar_smooth, yawn_detected):
    if yawn_detected:
        label = 'BOCA ABERTA (BOCEJO?)'
        color = (0, 0, 255)
    elif mar_smooth >= MAR_OPEN_THRESHOLD:
        label = 'BOCA ABERTA'
        color = (0, 165, 255)
    else:
        label = 'BOCA FECHADA'
        color = (0, 255, 0)

    cv2.putText(image_bgr, f'MAR: {mar_raw:.2f}', (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
    cv2.putText(image_bgr, f'MAR suavizado: {mar_smooth:.2f}', (20, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 220, 220), 2)
    cv2.putText(image_bgr, label, (20, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2)

def process_mar_and_yawn(
    detection_result,
    mar_history,
    high_mar_frames,
    yawn_banner_frames,
    cooldown_frames,
):
    """Atualiza estado de MAR/bocejo para o frame atual e devolve o novo estado."""
    # MAR bruto do frame atual.
    mar = 0.0
    face_landmarks_list = detection_result.face_landmarks
    if face_landmarks_list:
        # Usa somente a primeira face detectada (num_faces=1).
        mar = calculate_mar(face_landmarks_list[0])
        # Atualiza historico para calcular media movel.
        mar_history.append(mar)
    else:
        # Sem face: limpa historico e cancela contagem de evento em andamento.
        mar_history.clear()
        high_mar_frames = 0

    # MAR suavizado reduz oscilacoes tipicas da fala.
    mar_smooth = float(np.mean(mar_history)) if mar_history else 0.0

    # Diminui cooldown ate permitir nova deteccao.
    if cooldown_frames > 0:
        cooldown_frames -= 1

    # Conta apenas frames realmente fortes de abertura e fora de cooldown.
    if mar_smooth >= MAR_YAWN_LIKE_THRESHOLD and cooldown_frames == 0:
        high_mar_frames += 1
    # Se voltou para abertura baixa, reinicia o candidato a bocejo.
    elif mar_smooth < MAR_OPEN_THRESHOLD:
        high_mar_frames = 0

    # Confirma bocejo somente se a abertura alta persistiu por tempo suficiente.
    if high_mar_frames >= MIN_YAWN_FRAMES:
        yawn_banner_frames = YAWN_BANNER_FRAMES
        cooldown_frames = YAWN_COOLDOWN_FRAMES
        high_mar_frames = 0

    # Estado final da flag mostrada no frame atual.
    yawn_detected = yawn_banner_frames > 0
    # Conta regressiva da duracao da flag na tela.
    if yawn_banner_frames > 0:
        yawn_banner_frames -= 1

    return mar, mar_smooth, yawn_detected, high_mar_frames, yawn_banner_frames, cooldown_frames

# Funcao principal.
def main():  
    # Inicializa e valida o acesso ao video.
    capture = cv2.VideoCapture(0)
    if not capture.isOpened():
        print("Erro: Não foi possivel abrir o video.")
        sys.exit(-1)

    # Converte fps em delay entre frames 
    source_fps = capture.get(cv2.CAP_PROP_FPS)
    if source_fps <= 1e-6:
        source_fps = 30.0
    frame_delay_ms = max(1, int(round(1000.0 / (source_fps * PLAYBACK_SPEED))))

    # Configura o Face Landmarker (MediaPipe Tasks) com modelo local.
    base_options = python.BaseOptions(model_asset_path='face_landmarker.task')

    options = vision.FaceLandmarkerOptions(base_options=base_options,
                                           output_face_blendshapes=False,
                                           output_facial_transformation_matrixes=True,
                                           num_faces=1)
    detector = vision.FaceLandmarker.create_from_options(options)

    # Historico curto para suavizar variacoes rapidas do MAR frame a frame.
    mar_history = deque(maxlen=SMOOTHING_WINDOW)
    # Contador de frames consecutivos com MAR "alto" (candidato a bocejo).
    high_mar_frames = 0
    # Tempo de exibicao da flag de bocejo na tela apos confirmacao.
    yawn_banner_frames = 0
    # Janela de bloqueio entre eventos para evitar disparos repetidos.
    cooldown_frames = 0

    while True:
        # Captura um frame da webcam.
        success, frame = capture.read()
        if not success:
            print("Erro: Falha ao capturar o frame.")
            break

        # Desfaz espelhamento horizontal da camera para exibir orientacao real.
        frame = cv2.flip(frame, 1)

        # OpenCV usa BGR; o MediaPipe espera RGB.
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Converte o frame para o formato de imagem aceito pelo MediaPipe Tasks.
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Executa a deteccao de landmarks faciais no frame atual.
        detection_result = detector.detect(mp_image)

        # Processa estado de abertura da boca/bocejo para manter o loop principal limpo.
        mar, mar_smooth, yawn_detected, high_mar_frames, yawn_banner_frames, cooldown_frames = process_mar_and_yawn(
            detection_result,
            mar_history,
            high_mar_frames,
            yawn_banner_frames,
            cooldown_frames,
        )

        # Detecta direcao do olhar (frente/esquerda/direita) usando a posicao da iris.
        gaze_label = 'SEM ROSTO'
        gaze_color = (180, 180, 180)
        face_landmarks_list = detection_result.face_landmarks
        if face_landmarks_list and len(face_landmarks_list[0]) >= 478:
            lm = face_landmarks_list[0]

            # Centro da iris direita (indices 468..472) e esquerda (473..477).
            right_iris_x = float(np.mean([lm[idx].x for idx in range(468, 473)]))
            left_iris_x = float(np.mean([lm[idx].x for idx in range(473, 478)]))

            # Cantos horizontais de cada olho para normalizar a posicao da iris no intervalo [0, 1].
            right_eye_min_x = min(lm[33].x, lm[133].x)
            right_eye_max_x = max(lm[33].x, lm[133].x)
            left_eye_min_x = min(lm[362].x, lm[263].x)
            left_eye_max_x = max(lm[362].x, lm[263].x)

            right_width = right_eye_max_x - right_eye_min_x
            left_width = left_eye_max_x - left_eye_min_x

            if right_width > 1e-6 and left_width > 1e-6:
                right_ratio = (right_iris_x - right_eye_min_x) / right_width
                left_ratio = (left_iris_x - left_eye_min_x) / left_width
                gaze_ratio = (right_ratio + left_ratio) / 2.0

                if gaze_ratio < GAZE_LEFT_THRESHOLD:
                    gaze_label = 'OLHANDO PARA ESQUERDA'
                    gaze_color = (0, 255, 255)
                elif gaze_ratio > GAZE_RIGHT_THRESHOLD:
                    gaze_label = 'OLHANDO PARA DIREITA'
                    gaze_color = (0, 255, 255)
                else:
                    gaze_label = 'OLHANDO PARA FRENTE'
                    gaze_color = (255, 255, 0)

        # Desenha landmarks e exibe o resultado na tela.
        annotated_image = draw_landmarks_on_image(mp_image.numpy_view(), detection_result)
        output_bgr = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
        draw_mouth_flag(output_bgr, mar, mar_smooth, yawn_detected)
        cv2.putText(output_bgr, gaze_label, (20, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.75, gaze_color, 2)
        cv2.imshow('Annotated Image', output_bgr)

        # Encerra ao pressionar Esc (codigo 27).
        if cv2.waitKey(frame_delay_ms) & 0xFF == 27:
            break

    # Libera recursos da camera e fecha janelas do OpenCV.
    capture.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()