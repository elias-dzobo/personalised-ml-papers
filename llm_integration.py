from langchain_community.document_loaders import PyPDFLoader 
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import PGVector
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from database import * 
import instructor
from groq import Groq
from schema import Summary
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

host=os.getenv('host')
port=os.getenv('port')
dbname=os.getenv('dbname')
user=os.getenv('user')
password=os.getenv('password')


class RAG:
    def __init__(self):
        logger.info("Initializing RAG system")
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
        self.connection_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        self.model = ChatGroq(model_name="llama-3.3-70b-versatile")
        self.summary_model = instructor.from_groq(Groq())
        logger.info("RAG system initialized successfully")

    def query(self, source_name, question):
        logger.info(f"Querying source: {source_name}")
        try:
            store = PGVector(
                collection_name=source_name,
                connection_string=self.connection_string,
                embedding_function=self.embeddings,
                use_jsonb=True
            )
            
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.model,
                chain_type="stuff",
                retriever=store.as_retriever()
            )
            result = qa_chain.invoke({"query": question})["result"]
            logger.info(f"Successfully retrieved answer for query: {question[:100]}...")
            return result
        except Exception as e:
            logger.error(f"Error querying source {source_name}: {str(e)}")
            raise

    def save(self, url):
        logger.info(f"Starting to save document from URL: {url}")
        def sanitize(text: str) -> str:
            logger.debug("Sanitizing text chunk")
            # Remove NULL characters and other problematic characters
            text = text.replace('\x00', '')  # Remove NULL characters
            text = text.replace('\u0000', '')  # Remove Unicode NULL
            text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')  # Keep only printable characters and whitespace
            return text.strip()

        try:
            logger.info("Loading PDF document")
            loader = PyPDFLoader(url)
            documents = loader.load()
            logger.info(f"Successfully loaded PDF with {len(documents)} pages")

            logger.info("Splitting document into chunks")
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            chunks = text_splitter.split_documents(documents)
            logger.info(f"Created {len(chunks)} chunks from document")

            valid_chunks = []
            for chunk in chunks:
                # Ensure text is string and not empty
                if not isinstance(chunk.page_content, str):
                    logger.warning("Skipping chunk: not a string type")
                    continue
                if len(chunk.page_content.strip()) == 0:
                    logger.warning("Skipping chunk: empty content")
                    continue
                chunk.page_content = sanitize(chunk.page_content)
                valid_chunks.append(chunk)
            
            if not valid_chunks:
                error_msg = f"No valid text chunks found in {url}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.info(f"Saving {len(valid_chunks)} valid chunks to PGVector")
            PGVector.from_documents(
                documents=valid_chunks, 
                embedding=self.embeddings,
                collection_name=url,
                connection_string=self.connection_string,
                pre_delete_collection=True,
                use_jsonb=True
            )
            logger.info("Successfully saved document to PGVector")
        except Exception as e:
            logger.error(f"Error saving document from {url}: {str(e)}")
            raise

    def create_summary(self, url) -> Summary:
        logger.info(f"Creating summary for document: {url}")
        try:
            prompt = "analyse the research paper and generate a summary of the introduction, methodology, limitations, results, conclusions"
            logger.info("Querying document for initial summary")
            summary_unformatted = self.query(url, prompt)
            logger.info("Successfully retrieved initial summary")

            logger.info("Formatting summary using LLM")
            chat_completion = self.summary_model.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI research paper formatter. You will be given a snippet of research paper and you will need to format it into an introduction section, methodoloy, limitations, results, conclusion sections"
                    },
                    {
                        "role": "user",
                        "content": f"format {summary_unformatted} into the introduction, methodology, limitations, Results and Conclusion Sections",
                    }
                ],
                model="gemma2-9b-it",
                response_model=Summary
            )
            logger.info("Successfully created formatted summary")
            return chat_completion
        except Exception as e:
            logger.error(f"Error creating summary for {url}: {str(e)}")
            raise