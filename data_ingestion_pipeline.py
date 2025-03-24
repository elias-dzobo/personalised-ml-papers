import requests as re 
from bs4 import BeautifulSoup 
import re as regex
from prefect import task, flow
from pprint import pprint
import logging
from database import *
from datetime import datetime
import uuid
from llm_integration import RAG
import time 



URL = 'https://paperswithcode.com'
format = '%d %b %Y'
rag = RAG()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler('debug.log'), logging.StreamHandler()]
)

@task()
def test_connection():
    conn, cursor = connect_to_database()
    if conn:
        print("Connection successful")
        cursor.close()
        conn.close()
    else:
        print("Connection failed")

@task()
def ingest_data(url: str) -> str:
    logging.info("Starting data ingestion from %s", url)
    response = re.get(url, timeout=10)  # Added timeout for safety
    logging.info("Data ingestion complete")
    return response.content.decode('utf-8')


@task()
def parse_homepage(html: str) -> list:
    soup = BeautifulSoup(html, 'html5lib')
    # Find all paper sections on the homepage
    papers_divs = soup.find_all('div', attrs={'class': 'col-lg-9 item-content'})
    # Return a list of HTML strings for each paper
    return [str(div) for div in papers_divs]

@task()
def generate_data(paper_html: str) -> dict:
    logging.info("Starting processing of a paper snippet")
    paper = BeautifulSoup(paper_html, 'html5lib')
    paper_data = {}
    paper_data['topic'] = paper.h1.a.text
    paper_data['url'] = URL + paper.h1.a['href']
    paper_data['github'] = paper.p.span.a['href']
    spans_without_class = [span for span in paper.find_all('span') if not span.has_attr('class')]
    paper_data['tags'] = [tag.text for tag in spans_without_class]

    # Ingest the main page for this paper
    main_response = re.get(paper_data['url'])
    main_html = main_response.content.decode('utf-8')
    main_soup = BeautifulSoup(main_html, 'html5lib')

    # Extract the image from the main page if available
    image_table = main_soup.find_all('div', attrs={'class': 'col-lg-3 item-image-col'})
    if image_table:
        style_attr = image_table[0].a.div.get('style', '')
        match = regex.search(r"url\(['\"]?(.*?)['\"]?\)", style_attr)
        if match:
            paper_data['image'] = match.group(1)

    # Extract title and authors
    title_div = main_soup.find('div', class_='paper-title')
    if title_div:
        authors = title_div.find_all('span', attrs={'class': 'author-span'})
        if authors:
            paper_data['date'] = authors[0].text
            paper_data['authors'] = [author.text.strip() for author in authors][1:]
    
    # Extract abstract and PDF link
    abstract_div = main_soup.find('div', class_='paper-abstract')
    if abstract_div:
        paper_data['abstract'] = abstract_div.p.text.strip() if abstract_div.p else ''
        paper_data['pdf'] = abstract_div.a['href'] if abstract_div.a else ''

    logging.info("Finished processing paper: %s", paper_data.get('url', 'unknown URL'))

    return paper_data

@task
def validate_paper(paper: dict) -> bool:
    required_fields = ['topic', 'url', 'pdf', 'date']
    for field in required_fields:
        if field not in paper or not paper[field]:
            logging.error(f"Missing required field: {field}")
            return False
    return True


@task
def create_summary_and_save(papers):
    for paper in papers:
        url = paper['pdf'].replace('\x00', '').strip()
        if not url:
            logging.error("No URL found for paper: %s", paper['url'])
            continue

        #save paper to pgvector 
        rag.save(url)
        # create summary using llm_integration
        try:
            summary = rag.create_summary(url)
            paper['introduction'] = summary.Introduction
            paper['methodology'] = summary.Methodology
            paper['limitations'] = summary.Limitations
            paper['results'] = summary.Results
            paper['conclusions'] = summary.Conclusions
        except Exception as e:
            logging.error("Failed to create summary for paper: %s - %s", paper['url'], str(e))
            continue

    return papers
    

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
        logging.info("Table created successfully")
    except Exception as e:
        logging.error("Failed to create table: %s", str(e))
    finally:
        cursor.close()
        conn.close()
    
    

@task(retries=2)
def save_to_db(data):
    conn, cursor = connect_to_database()
    if not conn or not cursor:
        return False

    success_count = 0
    try:
        for idx, paper in enumerate(data):
            try:
                # Date parsing with error handling
                date_str = paper.get('date')
                parsed_date = None
                if date_str:
                    try:
                        parsed_date = datetime.strptime(date_str, format).date()
                    except ValueError:
                        logging.warning(f"Invalid date format for {paper['url']}: {date_str}")

                cursor.execute("""
                    INSERT INTO papers
                    (topic, abstract, url, github, authors, introduction, methodology, limitations, results, conclusions, image, date, tags, pdf)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO NOTHING
                """, (
                    paper['topic'],
                    paper.get('abstract', ''),
                    paper['url'],
                    paper.get('github', ''),
                    paper.get('authors', []),
                    paper.get('introduction', ''),
                    paper.get('methodology', ''),
                    paper.get('limitations', ''),
                    paper.get('results', ''),
                    paper.get('conclusions', ''),
                    paper.get('image', ''),
                    parsed_date,
                    paper.get('tags', []),
                    paper.get('pdf', '')
                ))
                success_count += cursor.rowcount  # Count successful inserts

            except Exception as e:
                logging.error(f"Failed to process paper {idx}: {str(e)}")
                logging.debug(f"Problematic paper data: {paper}")

        conn.commit()
        logging.info(f"Successfully inserted {success_count}/{len(data)} records")
    except Exception as e:
        logging.error(f"Database operation failed: {str(e)}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()
    return True

@flow()
def pipeline():
    test_connection()
    #step 0 - create postgres table 
    #create_papers_table()
    # Step 1: Ingest the homepage HTML
    homepage_html = ingest_data(URL)
    # Step 2: Parse the homepage to extract a list of paper HTML snippets
    papers_html_list = parse_homepage(homepage_html)
    # Step 3: Dynamically map the generate_data task over each paper snippet
    papers = [generate_data(paper_html) for paper_html in papers_html_list]
    # Step 4: Validate each paper data
    valid_papers = [p for p in papers if validate_paper(p)]

    #get summaries 
    valid_papers = create_summary_and_save(valid_papers)
    
    #save to db 
    save_to_db(valid_papers)
    

if __name__ == '__main__':
    pipeline()
