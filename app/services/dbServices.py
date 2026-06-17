import os
import sqlite3
import json
import numpy as np

class FaceDbSvc:

    def __init__(self, db_path:str):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def init_db(self):
        if os.path.exists(self.db_path):
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            #conn.execute("PRAGMA journal_mode=WAL")
        else:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS master_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    embedding TEXT NOT NULL
                )
            ''')
            self.conn.commit()

    def db_close(self):
        self.conn.close()
        self.cursor = None
        self.conn = None

    def save_embedding(self, name, embedding_array):
        if None in (self.conn, self.cursor):
            print("DB is not initialized, please initialize it first")
            return
        emb_string = json.dumps(embedding_array) # fallback: embedding_array.tolist()
        self.cursor.execute('INSERT INTO references (name, embedding) VALUES (?, ?)', (name, emb_string))
        self.conn.commit()

    def get_embeddings(self):
        if None in (self.conn, self.cursor):
            print("DB is not initialized, please initialize it first")
            return
        self.cursor.execute("SELECT name, embedding FROM master_embeddings")
        rows = self.cursor.fetchall()
        names = [row[0] for row in rows]
        # Creates a 2D matrix of shape (num_faces, embedding_dimension)
        matrix_embeddings = np.array([json.loads(row[1]) for row in rows])
        matrix_norms = np.linalg.norm(matrix_embeddings, axis=1)
        return names, matrix_norms

