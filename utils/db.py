import sqlite3
import hashlib
import os
from typing import Dict, Any

DB_PATH = './cardeals.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id TEXT PRIMARY KEY,
            link TEXT,
            data TEXT,
            status TEXT,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            removed_date TIMESTAMP,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def clear_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def hash_link(link: str) -> str:
    return hashlib.sha256(link.encode('utf-8')).hexdigest()

def upsert_car(link: str, data: str, status: str = 'active'):
    car_id = hash_link(link)
    conn = get_db_connection()
    c = conn.cursor()
    if status == 'active':
        c.execute('''
            INSERT INTO cars (id, link, data, status, last_seen, removed_date, created_date)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                data=excluded.data,
                status=excluded.status,
                last_seen=CURRENT_TIMESTAMP,
                removed_date=NULL,
                created_date=COALESCE(cars.created_date, CURRENT_TIMESTAMP)
        ''', (car_id, link, data, status))
    else:
        c.execute('''
            INSERT INTO cars (id, link, data, status, last_seen, removed_date, created_date)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, NULL, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                data=excluded.data,
                status=excluded.status,
                last_seen=CURRENT_TIMESTAMP,
                created_date=COALESCE(cars.created_date, CURRENT_TIMESTAMP)
        ''', (car_id, link, data, status))
    conn.commit()
    conn.close()

def mark_removed(link: str):
    import datetime
    car_id = hash_link(link)
    conn = get_db_connection()
    c = conn.cursor()
    removed_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''
        UPDATE cars SET status='removed', last_seen=CURRENT_TIMESTAMP, removed_date=? WHERE id=?
    ''', (removed_date, car_id))
    conn.commit()
    conn.close()

def get_all_cars():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, link, data, status, last_seen, removed_date, created_date FROM cars')
    rows = c.fetchall()
    conn.close()
    return rows
