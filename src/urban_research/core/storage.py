from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import DataPoint, Geography


class Storage:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS geographies (
                    geo_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    geo_type TEXT NOT NULL,
                    state_fips TEXT,
                    population INTEGER,
                    latitude REAL,
                    longitude REAL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS data_points (
                    geo_id TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL DEFAULT 0,
                    value REAL NOT NULL,
                    source TEXT NOT NULL,
                    vintage TEXT,
                    fetched_at TEXT NOT NULL,
                    PRIMARY KEY (geo_id, metric, year, month, source)
                );

                CREATE INDEX IF NOT EXISTS idx_dp_geo_metric
                    ON data_points(geo_id, metric);
                CREATE INDEX IF NOT EXISTS idx_dp_source
                    ON data_points(source);
                CREATE INDEX IF NOT EXISTS idx_dp_year
                    ON data_points(year);
                CREATE INDEX IF NOT EXISTS idx_geo_type
                    ON geographies(geo_type);
                CREATE INDEX IF NOT EXISTS idx_geo_pop
                    ON geographies(population);
            """)

    def upsert_geographies(self, geos: list[Geography]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.executemany(
                """INSERT INTO geographies
                       (geo_id, name, geo_type, state_fips, population, latitude, longitude, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(geo_id) DO UPDATE SET
                       name=excluded.name, geo_type=excluded.geo_type,
                       state_fips=excluded.state_fips, population=excluded.population,
                       latitude=excluded.latitude, longitude=excluded.longitude,
                       updated_at=excluded.updated_at""",
                [
                    (g.geo_id, g.name, g.geo_type.value, g.state_fips,
                     g.population, g.latitude, g.longitude, now)
                    for g in geos
                ],
            )
        return len(geos)

    def upsert_data_points(self, points: list[DataPoint]) -> int:
        with self._connect() as conn:
            conn.executemany(
                """INSERT INTO data_points
                       (geo_id, metric, year, month, value, source, vintage, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(geo_id, metric, year, month, source) DO UPDATE SET
                       value=excluded.value, vintage=excluded.vintage,
                       fetched_at=excluded.fetched_at""",
                [
                    (p.geo_id, p.metric, p.year, p.month, p.value,
                     p.source, p.vintage, p.fetched_at.isoformat())
                    for p in points
                ],
            )
        return len(points)

    def query_data(
        self,
        metric: str | None = None,
        geo_type: str | None = None,
        source: str | None = None,
        min_population: int | None = None,
        year: int | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        conditions: list[str] = []
        params: list[object] = []

        if metric:
            conditions.append("d.metric = ?")
            params.append(metric)
        if geo_type:
            conditions.append("g.geo_type = ?")
            params.append(geo_type)
        if source:
            conditions.append("d.source = ?")
            params.append(source)
        if min_population is not None:
            conditions.append("g.population >= ?")
            params.append(min_population)
        if year is not None:
            conditions.append("d.year = ?")
            params.append(year)

        query = """
            SELECT d.*, g.name, g.geo_type, g.population
            FROM data_points d
            JOIN geographies g ON d.geo_id = g.geo_id
        """
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY d.year DESC, d.value DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_sources_summary(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT source, metric,
                       COUNT(*) as records,
                       MIN(year) as min_year,
                       MAX(year) as max_year,
                       MAX(fetched_at) as last_fetched
                FROM data_points
                GROUP BY source, metric
                ORDER BY source, metric
            """).fetchall()
            return [dict(row) for row in rows]

    def get_geographies(
        self, geo_type: str | None = None, min_population: int | None = None,
    ) -> list[dict]:
        conditions: list[str] = []
        params: list[object] = []
        if geo_type:
            conditions.append("geo_type = ?")
            params.append(geo_type)
        if min_population is not None:
            conditions.append("population >= ?")
            params.append(min_population)

        query = "SELECT * FROM geographies"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY population DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
