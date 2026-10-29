"""Local SQLite storage for Focus Test System device cards and test history."""

from __future__ import annotations

import json
import math
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence


_MEASUREMENT_KEYS = (
    "torque",
    "current",
    "voltage",
    "temperature",
    "speed",
    "actuator_position",
)


class FocusDatabase:
    """Store device cards and every test run in a local SQLite database."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = Path(database_path) if database_path else self.default_path()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @staticmethod
    def default_path() -> Path:
        """Return a per-user writable location, including in a PyInstaller build."""
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base = Path(local_app_data)
        elif os.name == "nt":
            base = Path.home() / "AppData" / "Local"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return base / "FocusTestSystem" / "focus_test.sqlite3"

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create or upgrade the local database schema."""
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    serial_number TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    created_at TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS serial_sequences (
                    sequence_name TEXT PRIMARY KEY,
                    last_value INTEGER NOT NULL CHECK (last_value >= 0)
                );

                CREATE TABLE IF NOT EXISTS test_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    tested_at TEXT NOT NULL,
                    test_mode TEXT NOT NULL,
                    duration_seconds REAL NOT NULL DEFAULT 0,
                    result TEXT NOT NULL DEFAULT '',
                    torque REAL,
                    current REAL,
                    voltage REAL,
                    temperature REAL,
                    speed REAL,
                    actuator_position REAL,
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE RESTRICT
                );

                CREATE INDEX IF NOT EXISTS idx_test_records_device_date
                    ON test_records(device_id, tested_at DESC);

                CREATE TABLE IF NOT EXISTS test_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id INTEGER NOT NULL,
                    elapsed_seconds REAL NOT NULL,
                    torque REAL,
                    current REAL,
                    voltage REAL,
                    temperature REAL,
                    speed REAL,
                    actuator_position REAL,
                    FOREIGN KEY (test_id) REFERENCES test_records(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_test_samples_test_time
                    ON test_samples(test_id, elapsed_seconds);

                CREATE TABLE IF NOT EXISTS diagnostic_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    diagnosed_at TEXT NOT NULL,
                    error_code TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    likely_source TEXT NOT NULL DEFAULT '',
                    recommended_action TEXT NOT NULL DEFAULT '',
                    checked_items_json TEXT NOT NULL DEFAULT '[]',
                    technician_notes TEXT NOT NULL DEFAULT '',
                    modbus_data_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE RESTRICT
                );

                CREATE INDEX IF NOT EXISTS idx_diagnostic_records_device_date
                    ON diagnostic_records(device_id, diagnosed_at DESC);

                PRAGMA user_version = 3;
                """
            )
            diagnostic_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(diagnostic_records)")
            }
            if "modbus_data_json" not in diagnostic_columns:
                connection.execute(
                    "ALTER TABLE diagnostic_records "
                    "ADD COLUMN modbus_data_json TEXT NOT NULL DEFAULT '{}'"
                )

    @staticmethod
    def _clean_serial(serial_number: str) -> str:
        serial = str(serial_number).strip().upper()
        if not serial:
            raise ValueError("Seri numarası boş olamaz.")
        return serial

    @staticmethod
    def _number_or_none(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    def generate_serial_number(self) -> str:
        """Reserve and return the next local serial, for example FTS-000001."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT last_value FROM serial_sequences WHERE sequence_name = ?",
                ("device",),
            ).fetchone()
            next_value = (row["last_value"] if row else 0) + 1
            while connection.execute(
                "SELECT 1 FROM devices WHERE serial_number = ? COLLATE NOCASE",
                (f"FTS-{next_value:06d}",),
            ).fetchone():
                next_value += 1
            connection.execute(
                """
                INSERT INTO serial_sequences(sequence_name, last_value)
                VALUES (?, ?)
                ON CONFLICT(sequence_name) DO UPDATE SET last_value = excluded.last_value
                """,
                ("device", next_value),
            )
        return f"FTS-{next_value:06d}"

    def create_device(self, serial_number: str, notes: str = "") -> int:
        """Register a device card and return its database id."""
        serial = self._clean_serial(serial_number)
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO devices(serial_number, created_at, notes) VALUES (?, ?, ?)",
                    (serial, self._now(), str(notes).strip()),
                )
                return int(cursor.lastrowid)
        except sqlite3.IntegrityError as error:
            raise ValueError(f"Seri numarası {serial} zaten kayıtlı.") from error

    def save_test(
        self,
        serial_number: str,
        measurements: Mapping[str, Any],
        *,
        test_mode: str,
        duration_seconds: float = 0,
        result: str = "",
        samples: Sequence[Mapping[str, Any]] | None = None,
        tested_at: str | None = None,
    ) -> int:
        """Save one test summary and optional graph samples for an existing device."""
        serial = self._clean_serial(serial_number)
        mode = str(test_mode).strip()
        if not mode:
            raise ValueError("Test modu boş olamaz.")

        duration = self._number_or_none(duration_seconds)
        if duration is None or duration < 0:
            duration = 0.0

        with self._connect() as connection:
            device = connection.execute(
                "SELECT id FROM devices WHERE serial_number = ? COLLATE NOCASE",
                (serial,),
            ).fetchone()
            if device is None:
                raise ValueError(f"{serial} seri numaralı cihaz kayıtlı değil.")

            cursor = connection.execute(
                """
                INSERT INTO test_records (
                    device_id, tested_at, test_mode, duration_seconds, result,
                    torque, current, voltage, temperature, speed, actuator_position
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    device["id"],
                    tested_at or self._now(),
                    mode,
                    duration,
                    str(result).strip(),
                    *(self._number_or_none(measurements.get(key)) for key in _MEASUREMENT_KEYS),
                ),
            )
            test_id = int(cursor.lastrowid)

            if samples:
                sample_rows = []
                for sample in samples:
                    elapsed = self._number_or_none(sample.get("elapsed_seconds"))
                    if elapsed is None or elapsed < 0:
                        continue
                    sample_rows.append(
                        (
                            test_id,
                            elapsed,
                            *(self._number_or_none(sample.get(key)) for key in _MEASUREMENT_KEYS),
                        )
                    )
                connection.executemany(
                    """
                    INSERT INTO test_samples (
                        test_id, elapsed_seconds, torque, current, voltage,
                        temperature, speed, actuator_position
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    sample_rows,
                )
            return test_id

    def save_diagnostic(
        self,
        serial_number: str,
        *,
        error_code: str = "",
        description: str = "",
        likely_source: str = "",
        recommended_action: str = "",
        checked_items: Sequence[Mapping[str, Any] | str] = (),
        technician_notes: str = "",
        modbus_data: Mapping[str, Any] | None = None,
        diagnosed_at: str | None = None,
    ) -> int:
        """Save one guided fault diagnosis for an existing device card."""
        serial = self._clean_serial(serial_number)
        checked_json = json.dumps(list(checked_items), ensure_ascii=False, default=str)
        modbus_json = json.dumps(modbus_data or {}, ensure_ascii=False, default=str)
        with self._connect() as connection:
            device = connection.execute(
                "SELECT id FROM devices WHERE serial_number = ? COLLATE NOCASE",
                (serial,),
            ).fetchone()
            if device is None:
                raise ValueError(f"{serial} seri numaralı cihaz kayıtlı değil.")
            cursor = connection.execute(
                """
                INSERT INTO diagnostic_records (
                    device_id, diagnosed_at, error_code, description, likely_source,
                    recommended_action, checked_items_json, technician_notes,
                    modbus_data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    device["id"], diagnosed_at or self._now(),
                    str(error_code).strip(), str(description).strip(),
                    str(likely_source).strip(), str(recommended_action).strip(),
                    checked_json, str(technician_notes).strip(), modbus_json,
                ),
            )
            return int(cursor.lastrowid)

    def get_diagnostic_history(self, serial_number: str) -> list[dict[str, Any]]:
        """Return saved troubleshooting records for a device, newest first."""
        serial = self._clean_serial(serial_number)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT r.id, d.serial_number, r.diagnosed_at, r.error_code,
                       r.description, r.likely_source, r.recommended_action,
                       r.checked_items_json, r.technician_notes,
                       r.modbus_data_json
                FROM diagnostic_records AS r
                JOIN devices AS d ON d.id = r.device_id
                WHERE d.serial_number = ? COLLATE NOCASE
                ORDER BY r.diagnosed_at DESC, r.id DESC
                """,
                (serial,),
            ).fetchall()
            records = [dict(row) for row in rows]
            for record in records:
                record["checked_items"] = json.loads(record.pop("checked_items_json"))
                record["modbus_data"] = json.loads(record.pop("modbus_data_json") or "{}")
            return records

    def find_devices(self, search: str = "") -> list[dict[str, Any]]:
        """Search device serials and return each card with its test count."""
        query = str(search).strip()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT d.id, d.serial_number, d.created_at, d.notes,
                       COUNT(t.id) AS test_count,
                       MAX(t.tested_at) AS last_tested_at
                FROM devices AS d
                LEFT JOIN test_records AS t ON t.device_id = d.id
                WHERE d.serial_number LIKE ?
                GROUP BY d.id
                ORDER BY d.serial_number COLLATE NOCASE
                """,
                (f"%{query}%",),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_device(self, serial_number: str) -> dict[str, Any] | None:
        """Return one device card, or None when its serial is not registered."""
        serial = self._clean_serial(serial_number)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, serial_number, created_at, notes FROM devices "
                "WHERE serial_number = ? COLLATE NOCASE",
                (serial,),
            ).fetchone()
            return dict(row) if row else None

    def get_test_history(self, serial_number: str) -> list[dict[str, Any]]:
        """Return all saved tests for a device, newest first."""
        serial = self._clean_serial(serial_number)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT t.id, d.serial_number, t.tested_at, t.test_mode,
                       t.duration_seconds, t.result, t.torque, t.current,
                       t.voltage, t.temperature, t.speed, t.actuator_position
                FROM test_records AS t
                JOIN devices AS d ON d.id = t.device_id
                WHERE d.serial_number = ? COLLATE NOCASE
                ORDER BY t.tested_at DESC, t.id DESC
                """,
                (serial,),
            ).fetchall()
            return [dict(row) for row in rows]

    def delete_device(self, serial_number: str) -> bool:
        """Delete one card and all its saved tests, samples, and diagnostics."""
        serial = self._clean_serial(serial_number)
        with self._connect() as connection:
            device = connection.execute(
                "SELECT id FROM devices WHERE serial_number = ? COLLATE NOCASE",
                (serial,),
            ).fetchone()
            if device is None:
                return False
            device_id = int(device["id"])
            connection.execute(
                "DELETE FROM diagnostic_records WHERE device_id = ?", (device_id,)
            )
            connection.execute(
                "DELETE FROM test_records WHERE device_id = ?", (device_id,)
            )
            cursor = connection.execute(
                "DELETE FROM devices WHERE id = ?", (device_id,)
            )
            return cursor.rowcount > 0

    def delete_test_record(self, test_id: int) -> bool:
        """Delete one selected test; its graph samples are removed by cascade."""
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM test_records WHERE id = ?", (int(test_id),)
            )
            return cursor.rowcount > 0

    def delete_diagnostic_record(self, record_id: int) -> bool:
        """Delete one selected fault/diagnostic record."""
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM diagnostic_records WHERE id = ?", (int(record_id),)
            )
            return cursor.rowcount > 0

    def get_test_samples(self, test_id: int) -> list[dict[str, Any]]:
        """Return the saved graph samples for one test."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT elapsed_seconds, torque, current, voltage,
                       temperature, speed, actuator_position
                FROM test_samples
                WHERE test_id = ?
                ORDER BY elapsed_seconds, id
                """,
                (int(test_id),),
            ).fetchall()
            return [dict(row) for row in rows]
