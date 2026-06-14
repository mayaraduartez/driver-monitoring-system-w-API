import cv2 #openCv - camera, conversões de cor, filtros, desenho de texto, etc
import mediapipe as mp
import numpy as np  #trabalhar com arrays

#importo os modulos que vou usar do mediapipe
mp_hands  = mp.solutions.hands
mp_face   = mp.solutions.face_mesh
mp_draw   = mp.solutions.drawing_utils

# ---------------- Heurística: punho fechado ----------------
TIPS = [4, 8, 12, 16, 20] # ponto das pontas dos dedos
PIPS = [3, 6, 10, 14, 18] # ponto do meio dos dedos

def is_fist(lm, margin=0.01): #lm: lista das landmarks, margin: tolerância para reduzir falsos negativos
    """True se TODOS os dedos estiverem dobrados."""
    for tip_i, pip_i in zip(TIPS, PIPS): #faz pares tip, pip dedo a dedo 
        if lm[tip_i].y < lm[pip_i].y - margin:  # ponta acima do PIP => estendido 
            return False
    return True

# efeito de falso infravermelho (histograma)
def thermal_ir_jet(bgr):
    #O objetivo dessa parte do código é melhorar o contraste da imagem térmica (simulada).
    #Quando aplicamos o colormap (o “filtro colorido”), queremos que a escala de cores (do azul ao vermelho) use toda a faixa de tons possíveis (0–255),
    #não só uma parte pequena.
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) #converte para cinza

    # stretch por percentis para contraste estável
    lo, hi = np.percentile(gray, (5, 95))

    if hi - lo < 1: #np.percentile(gray, (5,95)) pega os níveis de brilho onde 5% dos pixels são mais escuros que lo e 5% são mais claros que hi. Isso ignora extremos (reflexos muito brilhantes, sombras muito escuras) que “achataram” o contraste.
        lo, hi = 0, 255


    gray = np.clip(gray, lo, hi) #Tudo abaixo de lo vira lo; tudo acima de hi vira hi.
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8) #Reescala para 0–255

    # contraste extra
    gray = cv2.convertScaleAbs(gray, alpha=1.4, beta=0) #Ganhar “punch” (contraste extra).

    # colormap JET 
    colored = cv2.applyColorMap(gray, cv2.COLORMAP_JET) #Aplica o colormap JET (o “falso IR”).

    # contornos estilo "tech"
    edges = cv2.Canny(gray, 80, 160) #Destaca contornos (boca, olhos, contorno da face, cabelo…) para dar um toque “tech”. 80 e 160 são os limiares de histerese (baixo/alto).
    edges3 = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR) #fundir com colored (que tem 3 canais). Precisamos que ambos tenham o mesmo formato.
    out = cv2.addWeighted(colored, 1.0, edges3, 0.6, 0) #Mistura final (cores + contornos).
    return out

# ---------------- Main ----------------
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) #abre o webcam 

blend = 0.0            # 0=normal, 1=IR
SMOOTH = 0.25          # velocidade do fade (maior = mais rápido)
hold = 0               # debounce do gesto
HOLD_FRAMES = 8        # ~1/4s a 30 fps

# estilos (pontos e linhas)
face_land_spec_tess = mp_draw.DrawingSpec(color=(255,255,255), thickness=1, circle_radius=1)
face_conn_spec_tess = mp_draw.DrawingSpec(color=(200,200,200), thickness=1)
face_conn_spec_cont = mp_draw.DrawingSpec(color=(255,255,255), thickness=2)

# inicializa mediapipe FaceMesh e Hands
with mp_face.FaceMesh(
    max_num_faces=2,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as face_mesh, mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as hands:

# loop principal
    while True:
        ok, frame = cap.read() #captura frame
        if not ok:
            break # se nao capturou mais frames, para

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) #conversao BGR -> RGB
        rgb.flags.writeable = False #dá um hint de performance (evita cópias desnecessárias).
        face_res = face_mesh.process(rgb)
        hand_res = hands.process(rgb)
        rgb.flags.writeable = True 

        # gesto: punho
        fist_now = False
        if hand_res.multi_hand_landmarks: # se tiver mão detectada
            for lms in hand_res.multi_hand_landmarks: # para cada mão detectada
                if is_fist(lms.landmark, margin=0.01): #verifica se é punho fechado
                    fist_now = True 
                    break

        # o contador é um para-choque contra ruído na detecção, garantindo uma experiência fluida.
        if fist_now: # se punho fechado agora
            hold = HOLD_FRAMES  # recarrega o contador quando o punho é visto
        else: # se não
            hold = max(0, hold - 1) # vai “gastando” aos poucos quando some

        effect_on =  (hold > 0)

        # fade suave
        target = 1.0 if effect_on else 0.0
        blend = (1.0 - SMOOTH) * blend + SMOOTH * target

        ir = thermal_ir_jet(frame)
        out = cv2.addWeighted(ir, blend, frame, 1.0 - blend, 0)

        
        # Hands
        if hand_res.multi_hand_landmarks:
            for lms in hand_res.multi_hand_landmarks:
                mp_draw.draw_landmarks(out, lms, mp_hands.HAND_CONNECTIONS)

        # Face - malha completa (tesselation)
        if face_res.multi_face_landmarks:
            for face_lms in face_res.multi_face_landmarks:
                mp_draw.draw_landmarks(
                    image=out,
                    landmark_list=face_lms,
                    connections=mp_face.FACEMESH_CONTOURS,
                    landmark_drawing_spec=mp_draw.DrawingSpec(
                        color=(0, 255, 0),   # Cor dos pontos
                        thickness=1,         # Espessura da linha
                        circle_radius=1   # <<< TAMANHO DOS PONTOS (padrão é 1 ou 2)

                    ),
                    connection_drawing_spec=mp_draw.DrawingSpec(
                        color=(255, 255, 255),  # Cor das linhas de conexão
                        thickness=1,            # Espessura das linhas
                        circle_radius=1         # Desnecessário aqui

                    )
                    
                )
            
        cv2.putText(out, "Filtro IR + Landmarks",
                    (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)

        # mostra    'out' (efeito + landmarks), não 'frame'
        cv2.imshow("Face Mesh (IR + mesmo padrao)", out)

        if cv2.waitKey(1) & 0xFF == 27:
    
            break

cap.release()
cv2.destroyAllWindows()
