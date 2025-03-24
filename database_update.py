from prefect import task, flow 
from database import Database
from llm_integration import RAG
import time

db = Database()
rag = RAG()

alter_sql = """
ALTER TABLE papers 
ADD COLUMN introduction TEXT,
ADD COLUMN methodology TEXT,
ADD COLUMN limitations TEXT,
ADD COLUMN results TEXT,
ADD COLUMN conclusions TEXT;
"""

select_sql = """
SELECT * FROM papers;
"""

update_sql = """
UPDATE papers 
SET introduction=%s, methodology=%s, limitations=%s, results=%s, conclusions=%s
WHERE id=%s;
"""

schema_sql = """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'papers';
"""

@task
def update_table():
    try:
        db.execute_query(alter_sql)
    except Exception as e:
        print(e)

@task 
def update_records():
    try:
        data = db.execute_query(select_sql)
        for paper in data:
       
            record_id = paper[0]
            url = paper[-7]
            print(f"record id { record_id} and url { url}")
            rag.save(url)
            summary = rag.create_summary(url)
            print(f"Updating record {record_id} with summary {summary}")
            db.execute_query(update_sql, (summary.Introduction, summary.Methodology, summary.Limitations, summary.Results, summary.Conclusions, record_id))
    except Exception as e:
        print(e)

@task 
def save_table_schema():
    results = db.execute_query(schema_sql)
    now = time.time()
    with open(f'schema_{now}.txt', 'w') as f:
        for col in results:
            f.write(f"{col}\n")



@flow
def update_database():
    #update_table()
    update_records()
    #save_table_schema()

if __name__ == "__main__":
    update_database()