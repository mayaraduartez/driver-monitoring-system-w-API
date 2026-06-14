import cv2
import numpy as np


def calcular_metricas_frame(frame):
    #converter para escala de cinza para facilitar o cálculo das métricas
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Calcular brilho, contraste, nitidez e ruído
    brilho = float(np.mean(gray))
    contraste = float(np.std(gray))

    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    nitidez = float(laplacian.var())

    ruido = float(np.mean(np.abs(gray - cv2.GaussianBlur(gray, (5, 5), 0))))

    return {
        "brilho": brilho,
        "contraste": contraste,
        "nitidez": nitidez,
        "ruido": ruido
    }


def ajustar_gamma(frame, gamma=1.2):
    inv_gamma = 1.0 / gamma

    tabela = np.array([
        ((i / 255.0) ** inv_gamma) * 255
        for i in range(256)
    ]).astype("uint8")

    return cv2.LUT(frame, tabela)


def reduzir_ruido(frame):
    return cv2.bilateralFilter(frame, 5, 50, 50)


def equalizar_histograma(frame):
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    l_equalizado = clahe.apply(l)
    lab_equalizado = cv2.merge((l_equalizado, a, b))

    return cv2.cvtColor(lab_equalizado, cv2.COLOR_LAB2BGR)


def aplicar_realce(frame):
    suavizado = cv2.GaussianBlur(frame, (0, 0), 1.0)

    return cv2.addWeighted(
        frame,
        1.5,
        suavizado,
        -0.5,
        0
    )


def preprocess_frame(frame):
    metricas = calcular_metricas_frame(frame)
    filtros_aplicados = []

    # Brilho baixo: clarear
    if metricas["brilho"] < 90:
        frame = ajustar_gamma(frame, gamma=1.4)
        filtros_aplicados.append("gamma_clarear")

    # Brilho alto: escurecer
    elif metricas["brilho"] > 180:
        frame = ajustar_gamma(frame, gamma=0.8)
        filtros_aplicados.append("gamma_escurecer")

    # Contraste baixo: CLAHE
    if metricas["contraste"] < 45:
        frame = equalizar_histograma(frame)
        filtros_aplicados.append("equalizacao_histograma")

    # Ruído alto: redução de ruído
    if metricas["ruido"] > 8:
        frame = reduzir_ruido(frame)
        filtros_aplicados.append("reducao_ruido")

    # Nitidez baixa: realce
    if metricas["nitidez"] < 80:
        frame = aplicar_realce(frame)
        filtros_aplicados.append("realce")

    return frame, metricas, filtros_aplicados