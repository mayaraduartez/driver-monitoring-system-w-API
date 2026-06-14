#Pegamos os pontos centrais do lábio superior e inferior (13 e 14).
#Medimos a distância vertical entre eles → mouth_distance.
#Pegamos dois pontos próximos dos olhos (por exemplo, 33 e 263 — cantos internos dos olhos).
#Calculamos a distância horizontal entre os olhos → serve como referência para o tamanho da face.
#Dividimos mouth_distance pela distância dos olhos → isso nos dá um valor relativo, independente do zoom.
#Definimos um limiar relativo (ex.: mouth_ratio > 0.70) → boca aberta.

import cv2 #openCV
import mediapipe as mp #framework do google
import math # calcular a distancia euclidiana entre pontos (chat sugeriu o math)

def euclidean_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

#declara modulos
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils #desenhar landmarks (pontos) e conexões no frame.
mp_hands = mp.solutions.hands


#abre o webcam no indice 0 (camera padrao)
cap = cv2.VideoCapture(0)


limiar = 0.70

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

        #se tiver resultado, percorre
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                # pontos da boca
                top_lip = face_landmarks.landmark[13] 
                bottom_lip = face_landmarks.landmark[14]

                # pontos dos olhos (para referência do tamanho da face)
                left_eye = face_landmarks.landmark[33]
                right_eye = face_landmarks.landmark[263]

                # distância da boca
                mouth_dist = euclidean_distance(top_lip, bottom_lip)
                # distância entre olhos
                eye_dist = euclidean_distance(left_eye, right_eye)

                # razão relativa
                mouth_ratio = mouth_dist / eye_dist
                
                #se esse result é maior que o limiar, avisa na janela em red
                if mouth_ratio > limiar:  # limiar definido la em cima
                    cv2.putText(frame, "Boca Aberta / Bocejo", (50, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                # desenha landmarks nos frames
                mp_drawing.draw_landmarks(# Defina o limiar mais sensível (exemplo: de 0.6 para 0.4)
limiar = 0.4  # ajuste conforme necessário

# Dentro do loop, para depuração (opcional)
print(f"mouth_ratio: {mouth_ratio:.2f}")

# O restante do código permanece igual
if mouth_ratio > limiar:
    cv2.putText(frame, "Boca Aberta / Bocejo", (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)# Defina o limiar mais sensível (exemplo: de 0.6 para 0.4)
limiar = 0.4  # ajuste conforme necessário

# Dentro do loop, para depuração (opcional)
print(f"mouth_ratio: {mouth_ratio:.2f}")

# O restante do código permanece igual
if mouth_ratio > limiar:
    cv2.putText(frame, "Boca Aberta / Bocejo", (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)# Defina o limiar mais sensível (exemplo: de 0.6 para 0.4)
limiar = 0.4  # ajuste conforme necessário

# Dentro do loop, para depuração (opcional)
print(f"mouth_ratio: {mouth_ratio:.2f}")

# O restante do código permanece igual
if mouth_ratio > limiar:
    cv2.putText(frame, "Boca Aberta / Bocejo", (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    frame,
                    face_landmarks,
                    mp_face_mesh.FACEMESH_CONTOURS)
        if hands_results.multi_hand_landmarks:
            for hand_landmarks in hands_results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)


        #exibe os frames
        cv2.imshow("Face Mesh", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

#fecha camera e janelas 
cap.release()
cv2.destroyAllWindows()