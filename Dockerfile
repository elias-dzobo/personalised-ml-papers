FROM python:3.11

WORKDIR /app

COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt 

ENV host=34.56.25.96
ENV port=5432
ENV dbname=ml-papers
ENV user=admin
ENV password=admin


COPY data_ingestion_pipeline.py .
COPY database.py .
COPY llm_integration.py .  
COPY schema.py .

CMD ['prefect', 'flow' 'run', 'data_ingestion_pipeline.py:pipeline']