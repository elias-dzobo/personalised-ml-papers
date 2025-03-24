from langchain_community.document_loaders import PyPDFLoader, TextLoader
from llm_integration import RAG
from database import * 
from schema import Summary

# conn, cursor = connect_to_database()

# sql_cmd = """CREATE EXTENSION IF NOT EXISTS vector"""

# cursor.execute(sql_cmd)
# conn.commit()

url = 'https://arxiv.org/pdf/2502.11946v2.pdf'

rag = RAG()

rag.save(url)
summary = rag.create_summary(url)
print(summary)

# summary = rag.create_summary(url)

# print(type(summary))
# print(summary)


# rag.save(url)

# print(rag.query(url, "what is the objective of this research paper?"))

# database = Database()

# sql = """
#         SELECT
#             column_name,
#             data_type
#         FROM
#             information_schema.columns
#         WHERE
#             table_name = 'papers';
#         """
# results = database.execute_query(sql)
# print(results)