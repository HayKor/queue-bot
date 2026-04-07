import sqlite3
import os

os.makedirs("data", exist_ok=True)

DB_NAME = "data/queues.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS queues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                message_id INTEGER,
                name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS queue_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                queue_id INTEGER,
                user_id INTEGER,
                full_name TEXT,
                position INTEGER,
                FOREIGN KEY(queue_id) REFERENCES queues(id)
            )
        """)
        conn.commit()

def create_queue(chat_id: int, name: str) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO queues (chat_id, name) VALUES (?, ?)", (chat_id, name))
        conn.commit()
        return cur.lastrowid

def set_queue_message(queue_id: int, message_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE queues SET message_id = ? WHERE id = ?", (message_id, queue_id))
        conn.commit()

def get_queue_by_message(chat_id: int, message_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM queues WHERE chat_id = ? AND message_id = ?", (chat_id, message_id))
        return cur.fetchone()

def join_queue(queue_id: int, user_id: int, full_name: str) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        # Проверка, есть ли уже пользователь в очереди
        cur.execute("SELECT id FROM queue_members WHERE queue_id = ? AND user_id = ?", (queue_id, user_id))
        if cur.fetchone():
            return False
            
        cur.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM queue_members WHERE queue_id = ?", (queue_id,))
        next_pos = cur.fetchone()[0]
        cur.execute("INSERT INTO queue_members (queue_id, user_id, full_name, position) VALUES (?, ?, ?, ?)",
                    (queue_id, user_id, full_name, next_pos))
        conn.commit()
        return True

def get_queue_members(queue_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM queue_members WHERE queue_id = ? ORDER BY position", (queue_id,))
        return cur.fetchall()

def _reindex_queue(conn, queue_id: int):
    """Схлопывает позиции в очереди, чтобы не было пропусков (1, 2, 3...)"""
    cur = conn.cursor()
    cur.execute("SELECT id FROM queue_members WHERE queue_id = ? ORDER BY position, id", (queue_id,))
    members = cur.fetchall()
    for new_pos, member in enumerate(members, start=1):
        cur.execute("UPDATE queue_members SET position = ? WHERE id = ?", (new_pos, member["id"]))

def pop_members(queue_id: int, count: int = 1):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM queue_members WHERE queue_id = ? ORDER BY position LIMIT ?", (queue_id, count))
        to_delete = cur.fetchall()
        for row in to_delete:
            cur.execute("DELETE FROM queue_members WHERE id = ?", (row["id"],))
        _reindex_queue(conn, queue_id)
        conn.commit()

def swap_members(queue_id: int, pos1: int, pos2: int) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, position FROM queue_members WHERE queue_id = ? AND position IN (?, ?)", (queue_id, pos1, pos2))
        members = cur.fetchall()
        if len(members) != 2:
            return False
            
        m1, m2 = members
        cur.execute("UPDATE queue_members SET position = ? WHERE id = ?", (m1["position"], m2["id"]))
        cur.execute("UPDATE queue_members SET position = ? WHERE id = ?", (m2["position"], m1["id"]))
        conn.commit()
        return True

def insert_member(queue_id: int, position: int, full_name: str):
    with get_connection() as conn:
        cur = conn.cursor()
        # Сдвигаем всех, кто равен или ниже заданной позиции, на +1
        cur.execute("UPDATE queue_members SET position = position + 1 WHERE queue_id = ? AND position >= ?", (queue_id, position))
        # user_id = 0, так как человек добавлен вручную
        cur.execute("INSERT INTO queue_members (queue_id, user_id, full_name, position) VALUES (?, 0, ?, ?)",
                    (queue_id, full_name, position))
        _reindex_queue(conn, queue_id)
        conn.commit()
