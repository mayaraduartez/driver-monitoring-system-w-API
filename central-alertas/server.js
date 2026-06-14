const express = require("express");
const cors = require("cors");
const sqlite3 = require("sqlite3").verbose();
const PORT = 3005;

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static("public"));

const API_TOKEN = "123456789abcdef"; // Token de autenticação para os dispositivos

function autenticarDispositivo(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader) {
    return res.status(401).json({
      success: false,
      message: "Token não informado"
    });
  }

  const token = authHeader.replace("Bearer ", "");

  if (token !== API_TOKEN) {
    return res.status(403).json({
      success: false,
      message: "Token inválido"
    });
  }

  next();
}

const db = new sqlite3.Database("./central_alertas.db");

db.run(`
  CREATE TABLE IF NOT EXISTS alertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    veiculo_id TEXT,
    motorista_id TEXT,
    dispositivo_id TEXT,
    data_hora_alerta TEXT,
    level TEXT,
    message TEXT,
    sleepiness_score REAL,
    distraction_score REAL,
    perclos_confidence REAL,
    payload TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
  )
`);

app.post("/api/alertas", autenticarDispositivo, (req, res) => {
  const data = req.body;

  db.run(
    `
    INSERT INTO alertas (
      veiculo_id,
      motorista_id,
      dispositivo_id,
      data_hora_alerta,
      level,
      message,
      sleepiness_score,
      distraction_score,
      perclos_confidence,
      payload
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `,
    [
      data.veiculo_id,
      data.motorista_id,
      data.dispositivo_id,
      data.data_hora,
      data.level,
      data.message,
      data.sleepiness_score,
      data.distraction_score,
      data.perclos_confidence,
      JSON.stringify(data)
    ],
    function (err) {
      if (err) {
        return res.status(500).json({
          success: false,
          message: "Erro ao salvar alerta",
          error: err.message
        });
      }

      return res.json({
        success: true,
        message: "Alerta recebido com sucesso",
        id: this.lastID
      });
    }
  );
});

app.get("/api/alertas", (req, res) => {
  db.all(
    "SELECT * FROM alertas ORDER BY id DESC LIMIT 100",
    [],
    (err, rows) => {
      if (err) {
        return res.status(500).json({
          success: false,
          error: err.message
        });
      }

      res.json(rows);
    }
  );
});

app.get("/api/alertas/:id", (req, res) => {

  db.get(
    "SELECT * FROM alertas WHERE id = ?",
    [req.params.id],
    (err, row) => {

      if (err) {
        return res.status(500).json({
          success: false,
          error: err.message
        });
      }

      res.json(row);
    }
  );

});

app.get("/api/status", (req, res) => {

  res.json({
    success: true,
    server: "online",
    timestamp: new Date()
  });

});

app.listen(PORT, () => {
  console.log(`Central de alertas rodando em http://localhost:${PORT}`);
});