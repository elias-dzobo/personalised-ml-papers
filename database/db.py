from prefect import flow, task
from database.database import *
from utils.logger import logger


@task(retries=2)
def create_papers_table():
    conn, cursor = connect_to_database()
    sql_cmd = """
    CREATE TABLE IF NOT EXISTS papers (
        id SERIAL PRIMARY KEY,
        topic TEXT NOT NULL,
        abstract TEXT,
        url TEXT UNIQUE NOT NULL,
        github TEXT NOT NULL,
        authors TEXT[],
        introduction TEXT,
        methodology TEXT,
        limitations TEXT,
        results TEXT,
        conclusions TEXT,
        image TEXT,
        date DATE,
        tags TEXT[],
        pdf TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    try:
        cursor.execute(sql_cmd)
        conn.commit()
        logger.info("Table created successfully")
    except Exception as e:
        logger.error("Failed to create table: %s", str(e))
    finally:
        cursor.close()
        conn.close()