import requests as re 
from bs4 import BeautifulSoup 
from pprint import pprint



URL = 'https://paperswithcode.com'


def ingest_data(URL):
    response = re.get(URL)
    content = response.content
    soup = BeautifulSoup(content, 'html5lib')

    return soup 

def fetch_homepage_data(soup):
    table = soup.find_all('div', attrs={'class': 'col-lg-9 item-content'})
    return table 
        

def generate_data(paper):
    papers = {}
    papers['topic'] = paper.h1.a.text
    papers['url'] = URL + paper.h1.a['href']
    papers['github'] = paper.p.span.a['href']
    spans_without_class = [span for span in paper.find_all('span') if not span.has_attr('class')]
    tags = [tag.text for tag in spans_without_class]
    papers['tags'] = tags

    # main page 
    main_page = ingest_data(URL + paper.h1.a['href'])
    # main page title section 
    new_table = main_page.find_all('div', attrs={'class': 'paper-title'})[0]
    authors = new_table.find_all('span', attrs={'class': 'author-span'})
    date = authors[0].text
    authors = [author.text.strip() for author in authors][1:]
    papers['date'] = date 
    papers['authors'] = authors

    #main page abstract section
    another_table = main_page.find_all('div', attrs={'class': 'paper-abstract'})[0]
    papers['abstract'] = another_table.p.text.strip()
    papers['pdf'] = another_table.a['href']

    return papers 

def flow():
    soup = ingest_data(URL)
    table = fetch_homepage_data(soup)
    papers_data = generate_data(table[0])
    pprint(papers_data)

flow()