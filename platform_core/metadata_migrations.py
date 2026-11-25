"""Idempotent migration of legacy local SQLite metadata into one database.

The migration preserves source databases and makes timestamped SQLite backups before
copying. It never deletes or overwrites legacy records. Conflicting primary keys are
kept from the destination; source-only records are inserted.
"""
from __future__ import annotations
import os, sqlite3, shutil
from pathlib import Path
from datetime import datetime, timezone

TABLE_ORDER = ["projects", "datasets", "versions", "scoped_settings", "settings_history", "experiments", "analysis_runs"]

def metadata_db_path() -> Path:
    return Path(os.getenv("METHANE_METADATA_DB") or "data/methane_metadata.sqlite3").expanduser().resolve()

def legacy_db_paths() -> list[Path]:
    root = Path(os.getenv("LOCAL_PROJECT_STORAGE_DIR", "data/local_workspace")).expanduser()
    candidates = [
        os.getenv("LOCAL_WORKSPACE_DB") or str(root / "workspace.sqlite3"),
        os.getenv("ANALYSIS_REGISTRY_PATH") or "data/analysis_registry.sqlite3",
        os.getenv("METHANE_RUN_REGISTRY") or "platform_data/analysis_runs.sqlite3",
    ]
    dest = metadata_db_path()
    out=[]
    for item in candidates:
        p=Path(item).expanduser().resolve()
        if p != dest and p.exists() and p not in out:
            out.append(p)
    return out

def migrate_legacy_metadata(destination: str | Path | None = None) -> dict:
    dest = Path(destination).expanduser().resolve() if destination else metadata_db_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    report={"destination":str(dest),"sources":[],"tables_copied":{},"rows_copied":{},"backups":[],"errors":[]}
    with sqlite3.connect(dest, timeout=30) as target:
        target.execute("PRAGMA journal_mode=WAL")
        target.execute("CREATE TABLE IF NOT EXISTS metadata_migrations (source_path TEXT PRIMARY KEY, migrated_at TEXT NOT NULL, result_json TEXT NOT NULL)")
        target.commit()
        migrated_sources = {r[0] for r in target.execute("SELECT source_path FROM metadata_migrations").fetchall()}
        for source in legacy_db_paths():
            if str(source) in migrated_sources:
                continue
            item={"source":str(source),"tables":{},"rows":{}}
            report["sources"].append(str(source))
            try:
                stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                backup=source.with_name(source.name+f".pre_migration_{stamp}.bak")
                if not backup.exists():
                    with sqlite3.connect(source) as src_con, sqlite3.connect(backup) as bak_con:
                        src_con.backup(bak_con)
                report["backups"].append(str(backup))
                with sqlite3.connect(source, timeout=30) as src:
                    src.row_factory=sqlite3.Row
                    names={r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    for table in TABLE_ORDER:
                        if table not in names: continue
                        schema=src.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()
                        if schema and schema[0]: target.execute(schema[0])
                        source_cols=[r[1] for r in src.execute(f'PRAGMA table_info("{table}")')]
                        target_cols={r[1] for r in target.execute(f'PRAGMA table_info("{table}")')}
                        cols=[c for c in source_cols if c in target_cols]
                        if not cols:
                            continue
                        col_select=','.join('"'+c.replace('"','""')+'"' for c in cols)
                        rows=src.execute(f'SELECT {col_select} FROM "{table}"').fetchall()
                        if rows:
                            placeholders=','.join('?' for _ in cols)
                            col_sql=','.join('"'+c.replace('"','""')+'"' for c in cols)
                            before=target.total_changes
                            target.executemany(f'INSERT OR IGNORE INTO "{table}" ({col_sql}) VALUES ({placeholders})', [tuple(r) for r in rows])
                            copied=target.total_changes-before
                        else: copied=0
                        item["tables"][table]=True; item["rows"][table]=copied
                        report["tables_copied"][table]=report["tables_copied"].get(table,0)+1
                        report["rows_copied"][table]=report["rows_copied"].get(table,0)+copied
                    target.execute("INSERT OR REPLACE INTO metadata_migrations VALUES (?,?,?)",(str(source),datetime.now(timezone.utc).isoformat(),str(item)))
                    target.commit()
                # Preserve useful non-auto indexes from the source after tables exist.
                with sqlite3.connect(source) as src:
                    for row in src.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"):
                        try: target.execute(row[0])
                        except sqlite3.DatabaseError: pass
                    target.commit()
            except Exception as exc:
                target.rollback(); item["error"]=f"{type(exc).__name__}: {exc}"; report["errors"].append(item)
    return report
