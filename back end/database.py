import sqlite3
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional

class F1Database:
    def __init__(self, db_path: str = "f1_sentiment.db"):
        """Initialized F1 sentiment database"""
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Creates database tables if not previously made"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS posts (
                        id TEXT PRIMARY KEY,
                        session TEXT NOT NULL,
                        title TEXT NOT NULL,
                        selftext TEXT,
                        score INTEGER,
                        created TEXT NOT NULL,
                        permalink TEXT,
                        author TEXT,
                        num_comments INTEGER,
                        race_name TEXT,
                        race_round INTEGER,
                        race_year INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS races (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        race_name TEXT NOT NULL,
                        race_round INTEGER NOT NULL,
                        race_year INTEGER NOT NULL,
                        race_date TEXT NOT NULL,
                        circuit_name TEXT,
                        country TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(race_name, race_round, race_year)
                    )
                ''')

                conn.commit()
                logging.info(f"Database initialzied at {self.db_path}")
            
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
            raise

    def insert_post(self, post_data: Dict, race_info: Dict):
        """
        Inserts a post into the db
        Parameters:
            post_data: Dictionary containing post information
            race_info: Dictionary containing race information
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    '''
                    INSERT OR IGNORE INTO posts 
                    (id, session, title, selftext, score, created, permalink, author, 
                     num_comments, race_name, race_round, race_year)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post_data['id'],
                    post_data['session'],
                    post_data['title'],
                    post_data['selftext'],
                    post_data['score'],
                    post_data['created'],
                    post_data['permalink'],
                    post_data['author'],
                    post_data['num_comments'],
                    race_info['raceName'],
                    race_info['round'],
                    race_info['season']
                ))

                conn.commit()
                
        except Exception as e:
            logging.error(f"Error inserting post {post_data.get('id', 'unknown')}: {e}")
    