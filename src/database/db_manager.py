import psycopg2
from psycopg2.extras import DictCursor
import os
from dotenv import load_dotenv
import json

load_dotenv()


class DBManager:
    def __init__(self):
        self.conn_params = {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
        }
        self.init_db()

    def init_db(self):
        """Initialize database and create required tables if they don't exist"""
        conn = psycopg2.connect(**self.conn_params)
        cur = conn.cursor()

        # Create detections table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS detections (id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                behavior_type VARCHAR(50) NOT NULL,
                confidence FLOAT NOT NULL,
                frame_path VARCHAR(255) NOT NULL,
                details TEXT,
                bbox JSON
            );
        """
        )

        conn.commit()
        cur.close()
        conn.close()

    def store_detection(self, timestamp, behavior_type, confidence, frame_path):
        """Store a new detection in the database"""
        conn = psycopg2.connect(**self.conn_params)
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO detections (timestamp, behavior_type, confidence, frame_path)
            VALUES (%s, %s, %s, %s)
        """,
            (timestamp, behavior_type, confidence, frame_path),
        )

        conn.commit()
        cur.close()
        conn.close()

    def get_detection_query(self):
        """Get the standard query for detections with proper timestamp formatting"""
        return """
            SELECT 
                id,
                TO_CHAR(timestamp AT TIME ZONE current_setting('TIMEZONE'), 'YYYY-MM-DD"T"HH24:MI:SS.MS') as timestamp,
                behavior_type,
                confidence,
                frame_path,
                details,
                bbox
            FROM detections
        """

    def process_detection_rows(self, rows):
        """Process database rows into detection dictionaries with proper frame paths"""
        detections = []
        for row in rows:
            detection = dict(row)
            if detection["frame_path"]:
                detection["frame_path"] = os.path.basename(detection["frame_path"])
            detections.append(detection)
        return detections

    def get_recent_alerts(self, limit=10):
        """Get recent detections from the database"""
        conn = psycopg2.connect(**self.conn_params)
        cur = conn.cursor(cursor_factory=DictCursor)

        query = (
            self.get_detection_query()
            + """
            ORDER BY timestamp DESC
            LIMIT %s
        """
        )
        cur.execute(query, (limit,))

        alerts = self.process_detection_rows(cur.fetchall())

        cur.close()
        conn.close()
        return alerts

    def get_recent_detections(self, limit=100):
        """Get recent detections ordered by timestamp"""
        conn = psycopg2.connect(**self.conn_params)
        cur = conn.cursor(cursor_factory=DictCursor)

        query = (
            self.get_detection_query()
            + """
            ORDER BY timestamp DESC
            LIMIT %s
        """
        )
        cur.execute(query, (limit,))

        detections = self.process_detection_rows(cur.fetchall())

        cur.close()
        conn.close()
        return detections

    def get_detections_by_type(self, behavior_type, limit=100):
        """Get detections filtered by behavior type"""
        conn = psycopg2.connect(**self.conn_params)
        cur = conn.cursor(cursor_factory=DictCursor)

        query = (
            self.get_detection_query()
            + """
            WHERE behavior_type = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        )
        cur.execute(query, (behavior_type, limit))

        detections = self.process_detection_rows(cur.fetchall())

        cur.close()
        conn.close()
        return detections
