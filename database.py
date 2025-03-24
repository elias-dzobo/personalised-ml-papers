import psycopg2
import dotenv
import os
# Load environment variables from.env file
dotenv.load_dotenv()

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv('host'),
            port=os.getenv('port'),
            dbname=os.getenv('dbname'),
            user=os.getenv('user'),
            password=os.getenv('password'),
            sslmode="disable",
        )
        self.cursor = self.conn.cursor()

    def execute_query(self, query, params=None):
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            # Return results if it's a SELECT query
            if query.strip().lower().startswith("select"):
                return self.cursor.fetchall()
            else:
                self.conn.commit()
                return None
        except psycopg2.Error as e:
            print(f"Error executing query: {e}")
            self.conn.rollback()
            return None

    def close_connection(self):
        self.cursor.close()
        self.conn.close()

def connect_to_database():
    try:
        conn = psycopg2.connect(
            host=os.getenv('host'),
            port=os.getenv('port'),
            dbname=os.getenv('dbname'),
            user=os.getenv('user'),
            password=os.getenv('password'),
            sslmode="disable",
            # sslrootcert="server-ca.pem"
        )
        print("Connected to the PostgreSQL database successfully")
    except psycopg2.Error as e:
        print(f"Error connecting to the PostgreSQL database: {e}")
        return None, None

    cursor = conn.cursor()

    return conn, cursor




#test_connection()


#connect_to_database()