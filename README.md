# Driver Monitoring System with API

Sistema para detecção de sonolência e desatenção de motoristas em tempo real utilizando Visão Computacional, Processamento Digital de Imagens e comunicação remota via API REST.

## Sobre o projeto

Este projeto implementa um protótipo de monitoramento de condutores capaz de identificar sinais visuais associados à sonolência e à desatenção, como:

- Fechamento ocular;
- Piscadas prolongadas;
- Bocejos;
- Direção do olhar;
- Olhar fora da via;
- Mão cobrindo boca, olhos ou apoiada na face;
- Combinação temporal de sinais de risco.

O sistema utiliza câmera comum, processamento local e técnicas de Visão Computacional para analisar o comportamento do motorista em tempo real. Também possui uma estrutura de envio remoto de alertas para uma central de monitoramento por meio de API REST, com fila local persistente em SQLite para funcionar mesmo sem conexão com a internet.

---

## Tecnologias utilizadas

- Python 3.12
- OpenCV
- MediaPipe
- SQLite
- Node.js
- Express.js
- API REST
- HTML
- CSS
- JavaScript

---

## Principais funcionalidades

- Captura de vídeo em tempo real
- Pré-processamento condicional da imagem
- Detecção de face, mãos e íris utilizando MediaPipe
- Cálculo das métricas EAR, MAR e PERCLOS
- Detecção de bocejos por análise temporal
- Detecção de oclusões faciais por mãos
- Análise da direção do olhar
- Classificação automática do nível de risco
- Alertas sonoros locais
- Armazenamento local em SQLite
- Sincronização automática dos alertas via API REST
- Central Web para monitoramento dos eventos

---

## Métricas utilizadas

### EAR (Eye Aspect Ratio)

Utilizado para estimar o grau de abertura dos olhos e detectar fechamentos prolongados.

### MAR (Mouth Aspect Ratio)

Utilizado para medir a abertura da boca e auxiliar na identificação de bocejos.

### PERCLOS (Percentage of Eye Closure)

Calcula o percentual de tempo em que os olhos permanecem fechados durante uma janela temporal.

---

## Arquitetura do sistema

O processamento ocorre seguindo o pipeline abaixo:

1. Captura do vídeo
2. Pré-processamento condicional da imagem
3. Detecção de face, mãos e íris
4. Extração dos landmarks
5. Cálculo das métricas EAR, MAR e PERCLOS
6. Análise temporal dos eventos
7. Fusão heurística das evidências
8. Classificação do nível de risco
9. Emissão de alerta local
10. Armazenamento em SQLite
11. Sincronização com a API REST

---

## Estrutura do projeto

```text
driver-monitoring-system-w-API/
│
├── assets/
├── central-alertas/
├── config/
├── database/
├── experiments/
├── models/
├── services/
├── sounds/
├── src/
├── README.md
└── TODO.md
```

---

## Como executar

### 1. Clone o repositório

```bash
git clone https://github.com/mayaraduartez/driver-monitoring-system-w-API.git
cd driver-monitoring-system-w-API
```

### 2. Crie um ambiente virtual

```bash
python -m venv venv
```

### 3. Ative o ambiente virtual

#### Windows

```bash
venv\Scripts\activate
```

#### Linux / macOS

```bash
source venv/bin/activate
```

### 4. Instale as dependências

```bash
pip install opencv-python mediapipe numpy requests math 
```

### 5. Execute o sistema

```bash
python src/main.py
```
---

## Executando a Central de Alertas

Entre na pasta da central:

```bash
cd central-alertas
```

Instale as dependências:

```bash
npm install
```

Inicie o servidor:

```bash
npm start
```

A central ficará responsável por receber os alertas enviados pelo sistema e exibi-los em tempo real.

---

## Privacidade

Este projeto prioriza a privacidade do motorista.

Nenhuma imagem ou vídeo é enviado para servidores externos.

Apenas metadados dos alertas são sincronizados, incluindo:

- Data e hora
- Tipo do alerta
- Nível de risco
- Escore de sonolência
- Escore de distração
- Identificação do motorista
- Identificação do veículo

---

## Classificação dos alertas

| Estado | Descrição |
|---------|-----------|
| 🟢 Normal | Nenhum risco identificado |
| 🟡 Atenção | Sinais moderados de risco |
| 🟠 Alerta de Sonolência | Evidências persistentes de fadiga |
| 🔵 Alerta de Distração | Condutor olhando fora da via |
| 🔴 Crítico | Sonolência e distração simultaneamente |

---

## Resultados

Os testes qualitativos demonstraram que o sistema é capaz de identificar:

- Piscadas prolongadas
- Fechamento ocular
- Bocejos
- Olhar fora da via
- Oclusões por mãos
- Apoio da cabeça
- Combinação de múltiplos sinais de risco

Além disso, o processamento local apresentou desempenho adequado para execução em computadores convencionais, preservando a privacidade do usuário.

---

## Trabalhos futuros

Entre as melhorias planejadas estão:

- Suporte à câmera infravermelha (NIR)
- Execução em Raspberry Pi
- Uso de modelos de Machine Learning
- Redução de falsos positivos
- Testes com múltiplos usuários
- Comparação entre alertas sonoros, visuais e hápticos
- Evolução da central de monitoramento
- Dashboard para análise histórica dos alertas

---

## Publicação científica

Este projeto foi desenvolvido como Trabalho de Conclusão de Curso do Instituto Federal Sul-rio-grandense (IFSul).

**Título:**

> Sistema para Detecção de Sonolência e Desatenção de Motoristas em Tempo Real por Visão Computacional

Autora:

**Mayara Gonçalves Duarte**

---

## Referência

Caso utilize este projeto em pesquisas, cite:

```bibtex
@article{duarte2026drivermonitoring,
  author = {Mayara Gonçalves Duarte and Marcel Corrêa},
  title = {Sistema para Detecção de Sonolência e Desatenção de Motoristas em Tempo Real por Visão Computacional},
  year = {2026},
  institution = {Instituto Federal Sul-rio-grandense}
}
```

---

## Licença

Este projeto foi desenvolvido para fins acadêmicos.

Sinta-se à vontade para utilizar como base para pesquisas e estudos, respeitando os créditos da autora.

---
⭐ Se este projeto foi útil para você, considere deixar uma estrela no repositório.
