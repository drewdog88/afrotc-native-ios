#!/usr/bin/env python3

"""
Restore data from a SQLite .db backup into the current Neon/PostgreSQL schema.
- Performs a dry-run first to compare table presence and record counts
- If not run with --apply, no changes are made to the Neon database
- On apply, clears target tables and inserts data while preserving IDs
- Resets sequences to avoid future ID conflicts

Usage:
  python restore_from_sqlite_backup.py --backup backups/<file>.db --dry-run
  python restore_from_sqlite_backup.py --backup backups/<file>.db --apply
"""

import argparse
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

load_dotenv('env.local')

# Tables to restore in dependency-safe order (parents first)
TABLE_ORDER = [
    # Delete/apply order should respect FK relationships when clearing:
    # We'll clear children first, then parents. For inserts we can go in parent->child order.
    # For simplicity, we reuse the same order for both, but implement child-first delete pass.
    'activity_log',
    'password_history',
    'recruitment_document',
    'external_link',
    'recruitment_event',
    'cadet',
    'potential_recruit',
    'university_contact',
    'user',
]


def get_neon_engine():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise RuntimeError('DATABASE_URL not set in env.local')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    engine = create_engine(database_url, connect_args={"sslmode": "require"})
    return engine


def read_sqlite_table(conn: sqlite3.Connection, table: str):
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM {table}')
    rows = cur.fetchall()
    columns = [d[0] for d in cur.description]
    return columns, rows


def neon_table_exists(engine, table: str) -> bool:
    insp = inspect(engine)
    return table in insp.get_table_names()


def clear_table(engine, table: str):
    with engine.begin() as conn:
        conn.execute(text('SET CONSTRAINTS ALL DEFERRED'))
        conn.execute(text(f'DELETE FROM "{table}"'))


def insert_rows(engine, table: str, columns, rows) -> int:
    if not rows:
        return 0

    # Get current table schema to handle missing columns
    with engine.begin() as conn:
        result = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position"))
        current_columns = [row[0] for row in result]

    # Map backup columns to current columns, providing defaults for missing ones
    column_mapping = {}
    for i, col in enumerate(columns):
        if col in current_columns:
            column_mapping[col] = i
        else:
            print(f"⚠️  Column '{col}' not found in current schema for table '{table}'")

    # Add default values for missing columns
    default_values = {
        'user': {
            'first_name': 'Admin',
            'last_name': 'User',
            'phone': None,
            'is_locked': False,
            'failed_login_attempts': 0,
            'password_changed_at': '2025-08-04 04:45:29.296116',
            'password_expires_at': None,
            'force_password_change': False,
            'secret_question': 'What is your favorite color?',
            'secret_answer_hash': 'pbkdf2:sha256:600000$default$default_hash'
        }
    }

    # Build SQL with current schema columns
    sql_columns = []
    for col in current_columns:
        sql_columns.append(f'"{col}"')

    sql = f'INSERT INTO "{table}" ({", ".join(sql_columns)}) VALUES ({", ".join(["%s"] * len(current_columns))})'

    # Known boolean columns per table
    BOOL_COLUMNS = {
        'user': {'is_active', 'is_locked', 'force_password_change'},
        'university_contact': {'is_active'},
        'external_link': {'is_active'},
        'recruitment_document': {'is_active'},
    }
    bool_cols = BOOL_COLUMNS.get(table, set())

    raw = engine.raw_connection()
    cur = raw.cursor()
    inserted = 0
    try:
        for row in rows:
            normalized = []
            for col in current_columns:
                if col in column_mapping:
                    v = row[column_mapping[col]]
                    # Normalize empty strings to NULLs for PG
                    if isinstance(v, str) and v == '':
                        v = None
                    # Coerce 0/1 to booleans for known boolean columns
                    if col in bool_cols and v is not None:
                        if isinstance(v, (int, float)):
                            v = bool(int(v))
                        elif isinstance(v, str) and v.strip() in {'0', '1'}:
                            v = v.strip() == '1'
                else:
                    # Use default value for missing column
                    defaults = default_values.get(table, {})
                    v = defaults.get(col, None)
                
                normalized.append(v)
            cur.execute(sql, normalized)
            inserted += 1
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        cur.close()
        raw.close()
    return inserted


def reset_identity_sequence(engine, table: str, id_column: str = 'id'):
    # Advance the sequence to max(id)
    with engine.begin() as conn:
        conn.execute(text(
            "SELECT setval(pg_get_serial_sequence(:t, :c), COALESCE((SELECT MAX(\"" + id_column + "\") FROM " + table + "), 0))"
        ).bindparams(t=table, c=id_column))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backup', required=False, help='Path to SQLite .db backup file')
    parser.add_argument('--apply', action='store_true', help='Apply changes (perform restore)')
    parser.add_argument('--dry-run', action='store_true', help='Dry-run only (default)')
    args = parser.parse_args()

    backup_path = args.backup
    if not backup_path:
        # Pick the most recent .db in backups/
        cand = [f for f in os.listdir('backups') if f.endswith('.db')]
        if not cand:
            raise SystemExit('No .db backups found in backups/')
        cand.sort(key=lambda x: os.path.getmtime(os.path.join('backups', x)), reverse=True)
        backup_path = os.path.join('backups', cand[0])

    if not os.path.exists(backup_path):
        raise SystemExit(f'Backup file not found: {backup_path}')

    print('=== Restore from SQLite Backup ===')
    print(f'Backup file: {backup_path}')
    print(f'Mode: {"APPLY" if args.apply else "DRY-RUN"}')
    print('=' * 40)

    # Open SQLite
    sqlite_conn = sqlite3.connect(backup_path)

    # Connect to Neon
    engine = get_neon_engine()

    # Compare tables and counts
    stats = []
    for table in TABLE_ORDER:
        try:
            cols, rows = read_sqlite_table(sqlite_conn, table)
            src_count = len(rows)
            exists = neon_table_exists(engine, table)
            stats.append((table, exists, src_count, cols, rows))
        except Exception as e:
            # Table doesn't exist in backup, skip it
            continue

    print('Table compatibility and row counts:')
    for table, exists, src_count, _, _ in stats:
        status = '✅ exists' if exists else '❌ missing in Neon'
        print(f'  - {table:<22} | {status:<18} | backup rows: {src_count}')

    missing = [t for t, exists, _, _, _ in stats if not exists]
    if missing:
        print('\n⚠️  Some tables are missing in Neon and will be skipped:', ', '.join(missing))

    if not args.apply:
        print('\nDry-run complete. Re-run with --apply to perform the restore.')
        return

    # Perform restore in order
    total_inserted = 0

    # First pass: clear all tables (children to parents)
    for table, exists, src_count, _, _ in stats:
        if not exists:
            continue
        print(f'Clearing table: {table}')
        clear_table(engine, table)

    # Second pass: insert (parents to children)
    # Sort by dependency order: user first, then others
    restore_order = []
    for table, exists, src_count, cols, rows in stats:
        if exists and rows:
            if table == 'user':
                restore_order.insert(0, (table, exists, src_count, cols, rows))
            else:
                restore_order.append((table, exists, src_count, cols, rows))
    
    for table, exists, src_count, cols, rows in restore_order:
        print(f'\nRestoring table: {table} ({len(rows)} rows)')
        inserted = insert_rows(engine, table, cols, rows)
        print(f'  Inserted: {inserted}')
        total_inserted += inserted
        if 'id' in cols:
            try:
                reset_identity_sequence(engine, table, 'id')
            except Exception:
                pass

    print('\n=== Restore complete ===')
    print(f'Total rows inserted: {total_inserted}')


if __name__ == '__main__':
    main()
