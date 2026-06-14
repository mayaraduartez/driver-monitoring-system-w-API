import sqlite3
import json
import os
from datetime import datetime
from config.config import SQLITE_DB_PATH


class AlertQueue:
    def __init__(self, db_path=SQLITE_DB_PATH):
        self.db_path = db_path
        self._ensure_database_dir()
        self._create_table()

    def _ensure_database_dir(self):
        database_dir = os.path.dirname(self.db_path)

        if database_dir and not os.path.exists(database_dir):
            os.makedirs(database_dir)

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alertas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    data_hora_alerta TEXT,
                    veiculo_id TEXT,
                    motorista_id TEXT,
                    dispositivo_id TEXT,
                    level TEXT NOT NULL,
                    message TEXT,
                    sleepiness_score REAL,
                    distraction_score REAL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDENTE',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    sent_at TEXT
                )
            """)

            conn.commit()

    def add_alert(self, level, payload):
        payload_json = json.dumps(payload, ensure_ascii=False)

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO alertas (
                    created_at,
                    data_hora_alerta,
                    veiculo_id,
                    motorista_id,
                    dispositivo_id,
                    level,
                    message,
                    sleepiness_score,
                    distraction_score,
                    payload,
                    status,
                    attempts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDENTE', 0)
            """, (
                datetime.now().isoformat(),
                payload.get("data_hora"),
                payload.get("veiculo_id"),
                payload.get("motorista_id"),
                payload.get("dispositivo_id"),
                level,
                payload.get("message"),
                payload.get("sleepiness_score"),
                payload.get("distraction_score"),
                payload_json
            ))

            conn.commit()

            return cursor.lastrowid

    def get_pending_alerts(self, limit=10):
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM alertas
                WHERE status = 'PENDENTE'
                ORDER BY id ASC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()

            alerts = []

            for row in rows:
                alert = dict(row)
                alert["payload"] = json.loads(alert["payload"])
                alerts.append(alert)

            return alerts

    def mark_as_sent(self, alert_id):
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE alertas
                SET status = 'ENVIADO',
                    sent_at = ?,
                    last_error = NULL
                WHERE id = ?
            """, (
                datetime.now().isoformat(),
                alert_id
            ))

            conn.commit()

    def mark_as_error(self, alert_id, error_message):
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE alertas
                SET attempts = attempts + 1,
                    last_error = ?
                WHERE id = ?
            """, (
                str(error_message),
                alert_id
            ))

            conn.commit()

    def count_pending(self):
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*)
                FROM alertas
                WHERE status = 'PENDENTE'
            """)

            return cursor.fetchone()[0]