import sqlite3
import asyncio
from threading import Lock

class Database:
    def __init__(self, db_name='inventory.db'):
        self.db_name = db_name
        self.lock = Lock()
        self.init_db()

    def init_db(self):
        with self.lock:
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    user_id INTEGER NOT NULL,
                    nft_name TEXT NOT NULL,
                    nft_link TEXT NOT NULL,
                    PRIMARY KEY (user_id, nft_name)
                )
            ''')
            conn.commit()
            conn.close()

    def add_nft(self, user_id, nft_name, nft_link):
        with self.lock:
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO inventory (user_id, nft_name, nft_link)
                VALUES (?, ?, ?)
            ''', (user_id, nft_name, nft_link))
            conn.commit()
            conn.close()

    def get_user_inventory(self, user_id):
        with self.lock:
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT nft_name, nft_link FROM inventory WHERE user_id = ?
            ''', (user_id,))
            rows = cursor.fetchall()
            conn.close()
            return [{"id": row[0], "link": row[1]} for row in rows]

db = Database()