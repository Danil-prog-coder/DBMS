# database.py
import sqlite3
from sqlite3 import Error
from typing import Optional, List, Dict
from config import DB_NAME

class Database:
    def __init__(self, db_file: str = DB_NAME):
        self.db_file = db_file
        self.create_tables()
        self.initialize_sample_data()

    def get_connection(self):
        try:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            return conn
        except Error as e:
            print(f"Database Error: {e}")
            return None

    def create_tables(self):
        conn = self.get_connection()
        if conn:
            cursor = conn.cursor()

            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица ценных бумаг (справочник)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS securities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    price REAL NOT NULL,
                    change_percent REAL DEFAULT 0,
                    description TEXT
                )
            ''')

            # Таблица покупок пользователя
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    security_id INTEGER,
                    amount REAL NOT NULL,
                    quantity REAL NOT NULL,
                    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (security_id) REFERENCES securities(id)
                )
            ''')

            conn.commit()
            conn.close()

    def initialize_sample_data(self):
        """Добавляет тестовые акции и облигации, если таблица пуста"""
        conn = self.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM securities")
            if cursor.fetchone()[0] == 0:
                stocks = [
                    ('GAZP', 'stock', 150.50, 2.3, 'Газпром'),
                    ('SBER', 'stock', 280.75, -1.2, 'Сбербанк'),
                    ('LKOH', 'stock', 6850.00, 0.8, 'Лукойл'),
                    ('YNDX', 'stock', 3200.50, 3.5, 'Яндекс'),
                    ('TCSG', 'stock', 1450.25, -0.5, 'Тинькофф'),
                ]
                bonds = [
                    ('OFZ-26234', 'bond', 1000.00, 0.1, 'ОФЗ 26234'),
                    ('OFZ-26238', 'bond', 980.50, 0.15, 'ОФЗ 26238'),
                    ('GAZP-B1', 'bond', 1050.00, 0.2, 'Газпром Капитал Б1'),
                    ('SBER-B2', 'bond', 1020.75, 0.18, 'Сбербанк Б2'),
                ]
                cursor.executemany(
                    "INSERT INTO securities (name, type, price, change_percent, description) VALUES (?, ?, ?, ?, ?)",
                    stocks + bonds
                )
                conn.commit()
            conn.close()

    def add_user(self, user_id: int) -> bool:
        conn = self.get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
                conn.commit()
                return True
            except Error as e:
                print(f"Error adding user: {e}")
                return False
            finally:
                conn.close()
        return False

    def get_balance(self, user_id: int) -> float:
        conn = self.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            return row['balance'] if row else 0.0
        return 0.0

    def set_balance(self, user_id: int, balance: float) -> bool:
        conn = self.get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (balance, user_id))
                conn.commit()
                return True
            except Error as e:
                print(f"Error setting balance: {e}")
                return False
            finally:
                conn.close()
        return False

    def update_balance(self, user_id: int, amount: float) -> bool:
        """Изменяет баланс на сумму amount (может быть отрицательной)"""
        conn = self.get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
                conn.commit()
                return True
            except Error as e:
                print(f"Error updating balance: {e}")
                return False
            finally:
                conn.close()
        return False

    def get_securities(self, security_type: str = None) -> List[Dict]:
        conn = self.get_connection()
        if conn:
            cursor = conn.cursor()
            if security_type:
                cursor.execute("SELECT * FROM securities WHERE type = ?", (security_type,))
            else:
                cursor.execute("SELECT * FROM securities")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        return []

    def get_security_by_id(self, security_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM securities WHERE id = ?", (security_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        return None

    def add_purchase(self, user_id: int, security_id: int, amount: float, quantity: float) -> bool:
        conn = self.get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO purchases (user_id, security_id, amount, quantity) VALUES (?, ?, ?, ?)",
                    (user_id, security_id, amount, quantity)
                )
                conn.commit()
                return True
            except Error as e:
                print(f"Error adding purchase: {e}")
                return False
            finally:
                conn.close()
        return False

    def get_user_purchases(self, user_id: int) -> List[Dict]:
        conn = self.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.*, s.name, s.type, s.price 
                FROM purchases p
                JOIN securities s ON p.security_id = s.id
                WHERE p.user_id = ?
                ORDER BY p.purchase_date DESC
            ''', (user_id,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        return []