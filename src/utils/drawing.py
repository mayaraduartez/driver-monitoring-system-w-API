# arquivo que fica as funcoes de desenho usadas no projeto, como desenhar os pontos de referência, etc
import numpy as np
from mediapipe.tasks.python.vision import drawing_utils
from mediapipe.tasks.python import vision

# funcao que desenha as landmarks na imagem (pontos e linhas)
def draw_landmarks_on_image(rgb_image, detection_result):
    annotated_image = np.copy(rgb_image)

    if not detection_result.face_landmarks:
        return annotated_image

    for face_landmarks in detection_result.face_landmarks:

        # CONTORNO DO ROSTO
        drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=face_landmarks,
            connections=vision.FaceLandmarksConnections.FACE_LANDMARKS_CONTOURS,
            landmark_drawing_spec=drawing_utils.DrawingSpec(color=(0,255,0), thickness=1, circle_radius=1),
            connection_drawing_spec=drawing_utils.DrawingSpec(color=(255,255,255), thickness=1)
        )

        # ÍRIS
        drawing_utils.draw_landmarks(
            annotated_image,
            face_landmarks,
            vision.FaceLandmarksConnections.FACE_LANDMARKS_LEFT_IRIS,
            None,
            drawing_utils.DrawingSpec(color=(0,255,255), thickness=1)
        )

        drawing_utils.draw_landmarks(
            annotated_image,
            face_landmarks,
            vision.FaceLandmarksConnections.FACE_LANDMARKS_RIGHT_IRIS,
            None,
            drawing_utils.DrawingSpec(color=(0,255,255), thickness=1)
        )

    return annotated_image
