# Arquivo que fica as funcoes matematicas usadas no projeto, como calculo de angulos, distancias, etc
import math

# distancia euclidiana 
def euclidean_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
