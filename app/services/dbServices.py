import os
import sqlite3
import json
import numpy as np

class FaceDbSvc:

    def __init__(self, db_path:str):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.names = None
        self.matrix_embeddings = None

    def init_db(self):
        if os.path.exists(self.db_path):
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.names, self.matrix_embeddings = self.get_embeddings()
            #conn.execute("PRAGMA journal_mode=WAL")
        else:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS master_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    embedding BLOB NOT NULL
                )
            ''')
            self.conn.commit()
        print(f"DB connection to {self.db_path} is OK")

    def db_close(self):
        self.conn.close()
        self.cursor = None
        self.conn = None
        self.names = None
        self.matrix_embeddings = None

    def save_embedding(self, name, embedding_array):
        if None in (self.conn, self.cursor):
            print("DB is not initialized, please initialize it first")
            return False
        #emb_string = json.dumps(embedding_array) # fallback: embedding_array.tolist()
        print(f"embed array shape: {embedding_array.shape}")
        print(f"embed array dtype: {embedding_array.dtype}")
        self.cursor.execute('INSERT INTO references (name, embedding) VALUES (?, ?)', (name, embedding_array.astype(np.float32).tobytes()))
        self.conn.commit()
        self.names, self.matrix_embeddings = self.get_embeddings()
        return True

    def get_embeddings(self):
        if None in (self.conn, self.cursor):
            print("DB is not initialized, please initialize it first")
            return
        self.cursor.execute("SELECT name, embedding FROM master_embeddings")
        rows = self.cursor.fetchall()
        if len(rows) >= 1:
            names = [row[0] for row in rows]
            # Creates a 2D matrix of shape (num_faces, embedding_dimension)
            matrix_embeddings = np.vstack([
                np.frombuffer(row[1], dtype=np.float32)
                for row in rows
            ]).astype(np.float32, copy=False)
            matrix_norms = np.linalg.norm(matrix_embeddings, axis=1)
            return names, matrix_norms
        else:
            return None, None

    def check_face_exists(self, query_embedding, threashold:float=0.65):
        if None in (self.names, self.matrix_embeddings):
            print("There are no faces yet")
            return
        similarities = self.matrix_embeddings @ query_embedding
        best_idx = np.argmax(similarities)
        best_score = similarities[best_idx]
        if best_score >= threashold:
            matched_name = self.names
        else:
            matched_name = None
        return matched_name
