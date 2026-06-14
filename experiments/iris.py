#Pegamos os pontos centrais do lábio superior e inferior (13 e 14).
#Medimos a distância vertical entre eles → mouth_distance.
#Pegamos dois pontos próximos dos olhos (por exemplo, 33 e 263 — cantos internos dos olhos).
#Calculamos a distância horizontal entre os olhos → serve como referência para o tamanho da face.
#Dividimos mouth_distance pela distância dos olhos → isso nos dá um valor relativo, independente do zoom.
#Definimos um limiar relativo (ex.: mouth_ratio > 0.70) → boca aberta.

import cv2 #openCV
import mediapipe as mp #framework do google
import math # calcular a distancia euclidiana entre pontos (chat sugeriu o math)

#declara modulos
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils #desenhar landmarks (pontos) e conexões no frame.
mp_hands = mp.solutions.hands
mp_styles = mp.solutions.drawing_styles

#abre o webcam no indice 0 (camera padrao)
cap = cv2.VideoCapture(0)

#function para medir a distancia em linha reta, para landmarks e tuplas (x,y)
def euclidean_distance(p1, p2):
    # Se for um landmark do mediapipe, usa .x e .y
    if hasattr(p1, 'x'):
        x1, y1 = p1.x, p1.y
    else:
        x1, y1 = p1  # é uma tupla (x, y)

    if hasattr(p2, 'x'):
        x2, y2 = p2.x, p2.y
    else:
        x2, y2 = p2

    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

limiar = 0.50
limiar_lip = 0.05  #limiar para distância mão-boca 

#incializa o FaceMesh
with mp_face_mesh.FaceMesh( #o with garante que o o modelo seja liberado automaticamente no final
    max_num_faces=2, # qtd de rosto
    refine_landmarks=True, # ativa landmarks detalhado pra olhos e boca
    min_detection_confidence=0.5, #nao entendi esse jogo de confianca ainda
    min_tracking_confidence=0.5
) as face_mesh, mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:

    while True:
        ret, frame = cap.read() #captura frame, se trouxe, ret é true
        if not ret:
            break # se nao capturou mais frames, para

        #conversao BGR -> RGB ???
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        #facemesh processa o frame e retorna em results com as landmarks no rosto 
        results = face_mesh.process(rgb)
        hands_results = hands.process(rgb)
        frame_h, frame_w, _ = frame.shape

        #se tiver resultado, percorre
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                # pontos da boca
                top_lip = face_landmarks.landmark[13] 
                bottom_lip = face_landmarks.landmark[14]
                lip_center = ((top_lip.x + bottom_lip.x) / 2, (top_lip.y + bottom_lip.y) / 2)
                lip_point = (int(lip_center[0] * frame_w), int(lip_center[1] * frame_h))
                cv2.circle(frame, lip_point, 5, (0, 255, 255), -1)

                # pontos dos olhos (para referência do tamanho da face)
                left_eye = face_landmarks.landmark[33]
                right_eye = face_landmarks.landmark[263]

                # distância da boca
                mouth_dist = euclidean_distance(top_lip, bottom_lip)

                # ======== IRIS TRACKING CORRIGIDO ========

                # Pontos de referência (corrigidos p/ câmera espelhada)
                right_inner = face_landmarks.landmark[33]
                right_outer = face_landmarks.landmark[133]

                left_inner  = face_landmarks.landmark[362]
                left_outer  = face_landmarks.landmark[263]

                # Centros das íris
                right_iris = face_landmarks.landmark[468]
                left_iris  = face_landmarks.landmark[473]

                def to_px(lm):
                    return int(lm.x * frame_w), int(lm.y * frame_h)

                r_iris_px = to_px(right_iris)
                l_iris_px = to_px(left_iris)

                cv2.circle(frame, r_iris_px, 3, (255, 0, 0), -1)
                cv2.circle(frame, l_iris_px, 3, (255, 0, 0), -1)

                # Razões
                def get_ratio(inner, iris, outer):
                    return euclidean_distance(inner, iris) / euclidean_distance(inner, outer)

                right_ratio = get_ratio(right_inner, right_iris, right_outer)
                left_ratio  = get_ratio(left_inner,  left_iris,  left_outer)

                gaze_ratio = (right_ratio + left_ratio) / 2

                # Classificação com thresholds ajustados
                if gaze_ratio < 0.40:
                    gaze_text = "Olhando para DIREITA"
                elif gaze_ratio > 0.65:
                    gaze_text = "Olhando para ESQUERDA"
                else:
                    gaze_text = "Olhando para FRENTE"

                cv2.putText(frame, gaze_text, (50, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)


                # distância entre olhos
                eye_dist = euclidean_distance(left_eye, right_eye)

                # razão relativa
                mouth_ratio = mouth_dist / eye_dist
                
                #se esse result é maior que o limiar, avisa na janela em red
                if mouth_ratio > limiar:  # limiar definido la em cima
                    cv2.putText(frame, "Boca Aberta / Bocejo", (50, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                # desenha landmarks nos frames
                mp_drawing.draw_landmarks(
                    frame,
                    face_landmarks,
                    mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=mp_drawing.DrawingSpec(
                        color=(0, 255, 0),   # Cor dos pontos
                        thickness=1,         # Espessura da linha
                        circle_radius=1   # <<< TAMANHO DOS PONTOS (padrão é 1 ou 2)

                    ),
                    connection_drawing_spec=mp_drawing.DrawingSpec(
                        color=(255, 255, 255),  # Cor das linhas de conexão
                        thickness=1,            # Espessura das linhas
                        circle_radius=1         # Desnecessário aqui

                    )
                )
                if hands_results.multi_hand_landmarks:
                    for hand_landmarks in hands_results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                        
                        palm_center = hand_landmarks.landmark[6]  # ponto central da mão

                        if lip_point:
                            dist_hand_mouth = euclidean_distance(palm_center, lip_center)

                            if dist_hand_mouth < limiar_lip:  # limiar definido para mão na boca
                                cv2.putText(frame, "Mao sobre a boca!", (50, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                                print("Distância mão-boca:", round(dist_hand_mouth, 3))

        #exibe os frames e fecha com ESC
        cv2.imshow("Face Mesh", frame)

        #espera 1ms e se apertar ESC (27) sai do loop
        if cv2.waitKey(1) & 0xFF == 27:
            break

#fecha camera e janelas 
cap.release()
cv2.destroyAllWindows()
