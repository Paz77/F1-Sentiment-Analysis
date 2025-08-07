import sqlite3
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import os

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
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS comments (
                    id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    link_id TEXT,
                    parent_id TEXT,
                    body TEXT,
                    score INTEGER,
                    created TEXT NOT NULL,
                    author TEXT,
                    session TEXT NOT NULL,
                    race_name TEXT,
                    race_round INTEGER,
                    race_year INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts (id)
                )''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_posts_session_round_year 
                    ON posts(session, race_round, race_year)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_posts_round_year 
                    ON posts(race_round, race_year)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_posts_created 
                    ON posts(created)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_races_round_year 
                    ON races(race_round, race_year)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_comments_post_id
                    ON comments(post_id)
                '''
                )

                conn.commit()
                logging.info(f"Database initialzied at {self.db_path}")
            
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
            raise

    def insert_post(self, post_data: Dict, race_info: Dict) -> bool:
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
                return True

        except Exception as e:
            logging.error(f"Error inserting post {post_data.get('id', 'unknown')}: {e}")
            return False
    
    def insert_comment(self, comment_data: Dict, post_id: str, race_info: Dict) -> bool:
        """
        Inserts comment into db
        Parameters:
            comment_data: dict containing comment info (duh)
            post_id: ID of parent post
            race_info: dict containing race info
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT OR IGNORE INTO comments 
                    (id, post_id, link_id, parent_id, body, score, created, author, 
                     session, race_name, race_round, race_year)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    comment_data['id'],
                    post_id,
                    comment_data['link_id'],
                    comment_data['parent_id'],
                    comment_data['body'],
                    comment_data['score'],
                    comment_data['created'],
                    comment_data['author'],
                    comment_data['session'],
                    race_info['raceName'],
                    race_info['round'],
                    race_info['season']
                ))

                conn.commit()
                return True
        
        except Exception as e:
            logging.error(f"Error inserting comment {comment_data.get('id', 'unknown')} : {e}")
            return False
    
    def insert_race(self, race_info: Dict):
        """
        Inserts race info into db
        Parameters:
            race_info: dict containing race info (duh)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT OR IGNORE INTO races 
                    (race_name, race_round, race_year, race_date, circuit_name, country)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    race_info['raceName'],
                    race_info['round'],
                    race_info['season'],
                    race_info['date'],
                    race_info.get('Circuit', {}).get('circuitName', ''),
                    race_info.get('Circuit', {}).get('Location', {}).get('country', '')
                ))

                conn.commit()

        except Exception as e:
            logging.error(f"Error inserting race {race_info.get('raceName', 'unknown')}: {e}")
    
    def get_posts_by_session(self, session: str, round_num: int, race_year: int) -> List[Dict]:
        """think imma stop doing this bc the parameters r self explanatory"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, session, title, selftext, score, created, permalink, 
                           author, num_comments, race_name, race_round, race_year
                    FROM posts 
                    WHERE session = ? AND race_round = ? AND race_year = ?
                    ORDER BY created DESC
                ''', (session, round_num, race_year))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        except Exception as e:
            logging.error(f"Error fetching posts by session: {e}")
            return []

    def get_comments_by_post(self, post_id: str) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, post_id, link_id, parent_id, body, score, created, 
                           author, session, race_name, race_round, race_year
                    FROM comments 
                    WHERE post_id = ?
                    ORDER BY created ASC
                ''', (post_id,))
                
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logging.error(f"Error fetching comments: {e}")
            return []
    
    def export_to_csv(self, session: str, race_round: int, race_year: int, filename: str):
        """
        Export posts and comments for a specific session to CSV.
        """
        try:
            posts = self.get_comments_by_round(session, race_round, race_year)
            all_records = []
            
            for post in posts:
                post_record = post.copy()
                post_record['type'] = 'post'
                all_records.append(post_record)
                
                # Add comment records
                comments = self.get_comments_by_post(post['id'])
                for comment in comments:
                    comment_record = comment.copy()
                    comment_record['type'] = 'comment'
                    all_records.append(comment_record)
            
            if all_records:
                df = pd.DataFrame(all_records)
                df.to_csv(filename, index=False)
                logging.info(f"Exported {len(all_records)} records to {filename}")
            else:
                logging.warning(f"No records found for export to {filename}")
                
        except Exception as e:
            logging.error(f"Error exporting to CSV: {e}")

    def get_comments_by_round(self, session: str, race_round: int, race_year: int) -> List[Dict]:
        """
        Get all comments for a specific session, round, and year using round number.
        Returns list of comment dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, post_id, link_id, parent_id, body, score, created, 
                           author, session, race_name, race_round, race_year
                    FROM comments 
                    WHERE session = ? AND race_round = ? AND race_year = ?
                    ORDER BY created ASC
                ''', (session, race_round, race_year))
            
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        except Exception as e:
            logging.error(f"Error fetching comments by round: {e}")
            return []

    def get_all_sessions_by_round(self, race_round: int, race_year: int) -> List[Dict]:
        """
        Get all posts and comments for all sessions of a specific race weekend.
        Returns list of dictionaries with 'type' field indicating 'post' or 'comment'
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get posts
                cursor.execute('''
                    SELECT id, session, title, selftext, score, created, permalink, 
                           author, num_comments, race_name, race_round, race_year
                    FROM posts 
                    WHERE race_round = ? AND race_year = ?
                    ORDER BY session, created DESC
                ''', (race_round, race_year))
                
                posts_columns = [description[0] for description in cursor.description]
                posts = [dict(zip(posts_columns, row)) for row in cursor.fetchall()]
                
                # Get comments
                cursor.execute('''
                    SELECT id, post_id, link_id, parent_id, body, score, created, 
                           author, session, race_name, race_round, race_year
                    FROM comments 
                    WHERE race_round = ? AND race_year = ?
                    ORDER BY session, created ASC
                ''', (race_round, race_year))
                
                comments_columns = [description[0] for description in cursor.description]
                comments = [dict(zip(comments_columns, row)) for row in cursor.fetchall()]
                
                # Add type field to distinguish posts and comments
                for post in posts:
                    post['type'] = 'post'
                for comment in comments:
                    comment['type'] = 'comment'
                
                # Combine and return
                return posts + comments
        
        except Exception as e:
            logging.error(f"Error fetching all sessions by round: {e}")
            return []

    def get_race_info_by_round(self, race_round: int, race_year: int) -> Optional[Dict]:
        """
        Get race information for a specific round and year.

        Returns race information dictionary or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT race_name, race_round, race_year, race_date, circuit_name, country
                    FROM races 
                    WHERE race_round = ? AND race_year = ?
                ''', (race_round, race_year))
            
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
        
        except Exception as e:
            logging.error(f"Error fetching race info by round: {e}")
            return None

    def export_everything(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                print("Tables found:", tables)

                for table_name in tables:
                    table_name = table_name[0]
                    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                    df.to_csv(f"{table_name}.csv", index=False)
                    print(f"Exported {table_name} to {table_name}.csv")
                
        except Exception as e:
            print(f"Error exporting database: {e}")

    def get_session_data(self, session: str, race_round: int, race_year: int) -> Dict[str, List[Dict]]:
        """
        Get both posts and comments for a specific session.
        
        Returns:
            Dictionary with 'posts' and 'comments' keys
        """
        try:
            posts = self.get_posts_by_session(session, race_round, race_year)
            comments = self.get_comments_by_round(session, race_round, race_year)
            
            return {
                'posts': posts,
                'comments': comments
            }
        
        except Exception as e:
            logging.error(f"Error fetching session data: {e}")
            return {'posts': [], 'comments': []}

    def add_sentiment_table(self):
        """Add sentiment analysis table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DROP TABLE IF EXISTS sentiment_scores')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sentiment_scores (
                    id TEXT PRIMARY KEY,
                    ensemble_score REAL,
                    sentiment_category TEXT,
                    vader_score REAL,
                    textblob_polarity REAL,
                    textblob_subjectivity REAL,
                    bert_score REAL,
                    bert_label TEXT,
                    model_agreement REAL,
                    cleaned_text TEXT,
                    tokens TEXT,
                    created_at TIMESTAMP, 
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id) REFERENCES posts(id) ON DELETE CASCADE,
                    FOREIGN KEY (id) REFERENCES comments(id) ON DELETE CASCADE
                )
                ''')
                
                conn.commit()
                logging.info("Sentiment scores table created")
                
        except Exception as e:
            logging.error(f"Error creating sentiment table: {e}")
            raise

    def save_sentiment_scores(self, sentiment_data: pd.DataFrame):
        """Save sentiment scores to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for _, row in sentiment_data.iterrows():
                    cursor = conn.cursor()

                    cursor.execute('''
                        SELECT created FROM posts WHERE id = ?
                        UNION
                        SELECT created FROM comments WHERE id = ?
                    ''', (row['id'], row['id']))

                    result = cursor.fetchone()
                    created_time  = result[0] if result else None
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO sentiment_scores 
                        (id, vader_score, cleaned_text, tokens, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        row['id'],
                        row['vader_score'],
                        row['cleaned'],
                        ' '.join(row['tokens']) if isinstance(row['tokens'], list) and len(row['tokens']) > 0 else '',
                        created_time
                    ))
                
                conn.commit()
                logging.info(f"Saved {len(sentiment_data)} sentiment scores")
                
        except Exception as e:
            logging.error(f"Error saving sentiment scores: {e}")
            raise

    def get_sentiment(self, session: str, race_round: int, race_year: int) -> List[Dict]:
        """
        Gets all sentiment for given session, race, and year.  
        Returns list of dictionaries with sentiment
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id FROM posts
                    WHERE session = ? AND race_round = ? AND race_year = ?
                ''', (session, race_round, race_year))
                post_ids = [row[0] for row in cursor.fetchall()]

                cursor.execute('''
                    SELECT id FROM comments 
                    WHERE session = ? AND race_round = ? AND race_year = ?
                ''', (session, race_round, race_year))
                comment_ids = [row[0] for row in cursor.fetchall()]

                all_ids = post_ids + comment_ids
                if not all_ids:
                    return []
                
                placeholders = ','.join('?' for _ in all_ids)
                query = f'''
                    SELECT * FROM sentiment_scores
                    Where id IN ({placeholders})
                '''
                cursor.execute(query, all_ids)
                columns = [description[0] for description in cursor.description]

                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logging.error(f"Error fetching sentiment for session {session}, round {race_round}, year {race_year}: {e}")
            return []

    def add_visualizations_table(self):
        """add table to store visualizations"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS visualizations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session TEXT NOT NULL,
                        race_round INTEGER NOT NULL,
                        race_year INTEGER NOT NULL,
                        visualization_type TEXT NOT NULL,
                        image_data BLOB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(session, race_round, race_year, visualization_type)
                    )
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_visualizations_session_round_year 
                    ON visualizations(session, race_round, race_year)
                ''')
                
                conn.commit()
                logging.info("Visualizations table created")
                
        except Exception as e:
            logging.error(f"Error creating visualizations table: {e}")
            raise

    def save_visualization(self, session: str, race_round: int, race_year: int, visualization_type: str, image_data: bytes) -> bool:
        """saves visualization to db"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                INSERT OR REPLACE INTO visualizations 
                (session, race_round, race_year, visualization_type, image_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (session, race_round, race_year, visualization_type, image_data))
            
            conn.commit()
            logging.info(f"Saved {visualization_type} visualization for {session}, Round {race_round}, {race_year}")
            return True
            
        except Exception as e:
            logging.error(f"Error saving visualization: {e}")
            return False

    def get_visualization(self, session: str, race_round: int, race_year: int, visualization_type: str) -> Optional[bytes]:
        """retrieves visualization from db"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
            
                cursor.execute('''
                    SELECT image_data FROM visualizations
                    WHERE session = ? AND race_round = ? AND race_year = ? AND visualization_type = ?
                ''', (session, race_round, race_year, visualization_type))
            
                result = cursor.fetchone()
                return result[0] if result else None
            
        except Exception as e:
            logging.error(f"Error retrieving visualization: {e}")
            return None

    def list_available_visualizations(self) -> List[Dict]:
        """Get a list of all available visualizations in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT session, race_round, race_year, visualization_type, created_at
                    FROM visualizations
                    ORDER BY race_year DESC, race_round DESC, session, visualization_type
                ''')
            
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        except Exception as e:
            logging.error(f"Error listing visualizations: {e}")
            return []

"""
def main():
    db = F1Database()
    db.export_everything()

if __name__ == "__main__":
    main()
"""