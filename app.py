import os
import time
import re
from dotenv import load_dotenv
from langchain.sql_database import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_sql_query_chain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
import mysql.connector
import streamlit as st
import logging
from functools import lru_cache

# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO)

# Load environment variables
load_dotenv()

# Initialize MySQL connection
def get_db_connection():
    try:
        return mysql.connector.connect(
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            host=os.getenv("MYSQL_HOST"),
            database=os.getenv("MYSQL_DATABASE")
        )
    except mysql.connector.Error as e:
        logging.error(f"Database connection failed: {str(e)}")
        return None

# Initialize LangChain components
db_uri = f"mysql+mysqlconnector://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}/{os.getenv('MYSQL_DATABASE')}"
try:
    db = SQLDatabase.from_uri(db_uri)
except Exception as e:
    logging.error(f"Failed to initialize SQLDatabase: {str(e)}")
    st.error(f"Database connection error: {str(e)}")
    exit(1)

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))

# Define database schema
schema_info = """
Table: students
- roll_no: INT, PRIMARY KEY
- first_name: VARCHAR(100), NOT NULL
- last_name: VARCHAR(100), NOT NULL
- age: TINYINT UNSIGNED, NOT NULL
- class_id: INT, FOREIGN KEY to classes(class_id)
- section_id: INT, FOREIGN KEY to sections(section_id)
- scholarship_id: INT, FOREIGN KEY to scholarships(scholarship_id), NULLABLE
- bank_account_id: INT, FOREIGN KEY to bankdetails(bank_account_id), NULLABLE

Table: parents
- parent_id: INT, PRIMARY KEY
- student_roll_no: INT, FOREIGN KEY to students(roll_no)
- parent_name: VARCHAR(200), NOT NULL
- relation: VARCHAR(50), NOT NULL

Table: subjects
- subject_id: INT, PRIMARY KEY
- subject_name: VARCHAR(100), NOT NULL

Table: scholarships
- scholarship_id: INT, PRIMARY KEY
- scholarship_name: VARCHAR(100), NOT NULL
- amount: DECIMAL(10,2), NOT NULL

Table: marks
- mark_id: INT, PRIMARY KEY
- student_roll_no: INT, FOREIGN KEY to students(roll_no)
- subject_id: INT, FOREIGN KEY to subjects(subject_id)
- marks_obtained: DECIMAL(5,2), NOT NULL

Table: bankdetails
- bank_account_id: INT, PRIMARY KEY
- student_roll_no: INT, FOREIGN KEY to students(roll_no)
- bank_name: VARCHAR(100), NOT NULL
- account_number: VARCHAR(30), NOT NULL
- ifsc_code: VARCHAR(20), NOT NULL

Table: classes
- class_id: INT, PRIMARY KEY
- class_name: VARCHAR(50), NOT NULL
- section_id: INT, FOREIGN KEY to sections(section_id)

Table: sections
- section_id: INT, PRIMARY KEY
- section_name: CHAR(1), NOT NULL
"""

# Custom prompt for SQL query generation
sql_prompt = PromptTemplate(
    input_variables=["input", "top_k", "table_info"],
    template="""
    You are a MySQL expert. Given a user question and the database schema, create a syntactically correct MySQL query to retrieve the relevant data. Use JOINs for related tables, avoid subqueries where possible, and limit results to {top_k} for performance. Return ONLY the SQL query as plain text, without any Markdown, code blocks (```sql or ```), or additional text.

    User question: {input}
    Database schema: {table_info}

    SQL Query:
    """
)

# Custom prompt for response generation
response_prompt = PromptTemplate(
    input_variables=["query", "results", "history"],
    template="""
    You are a helpful assistant. Based on the SQL query, its results, and the conversation history, provide a clear, concise response in plain English. Avoid technical terms and format the response conversationally. Use the history to maintain context for follow-up questions.

    Conversation History: {history}
    SQL Query: {query}
    Results: {results}

    Response:
    """
)

# Initialize SQL query chain with schema
sql_chain = create_sql_query_chain(llm=llm, db=db, prompt=sql_prompt.partial(table_info=schema_info), k=5)

# Initialize conversation memory
memory = ConversationBufferMemory(input_key="input", memory_key="history")

# Cache for frequent queries
@lru_cache(maxsize=100)
def cached_sql_query(sanitized_input, top_k):
    return sql_chain.invoke({"question": sanitized_input, "top_k": top_k})

# Function to sanitize user input
def sanitize_input(user_input):
    dangerous_patterns = [r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b', r'--', r';', r'\*']
    sanitized = user_input
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
    return sanitized

# Function to clean SQL query
def clean_sql_query(query):
    # Remove Markdown code block markers and surrounding whitespace
    cleaned = re.sub(r'```sql\s*|\s*```', '', query, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    return cleaned

# Function to execute SQL query safely
def execute_query(query):
    try:
        conn = get_db_connection()
        if not conn:
            return "Failed to connect to the database."
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    except mysql.connector.Error as e:
        logging.error(f"Query failed: {query}\nError: {str(e)}")
        return f"Error executing query: {str(e)}"

# Function to generate response with retry logic
def generate_response(user_input):
    try:
        sanitized_input = sanitize_input(user_input)
        max_retries = 3
        retry_delay = 6  # seconds, based on Gemini API rate limit error

        for attempt in range(max_retries):
            try:
                sql_query = cached_sql_query(sanitized_input, 5)
                cleaned_query = clean_sql_query(sql_query)
                logging.info(f"Executing query: {cleaned_query}")
                results = execute_query(cleaned_query)
                if isinstance(results, str):
                    return results  # Error message
                results_str = str(results) if results else "No results found."

                # Update conversation memory
                memory.save_context({"input": sanitized_input}, {"output": results_str})

                # Get conversation history
                history = memory.load_memory_variables({})["history"]

                # Generate response using the LLM directly with response_prompt
                response = llm.invoke(
                    response_prompt.format(query=cleaned_query, results=results_str, history=history)
                ).content
                return response
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    logging.warning(f"Rate limit exceeded, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logging.error(f"Response generation failed: {str(e)}")
                    return f"Error generating response: {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return f"Error generating response: {str(e)}"

# Streamlit frontend
def main():
    st.title("School Database Q&A Bot (Powered by Gemini)")
    st.write("Ask about students, parents, marks, scholarships, or classes, and get answers in plain English!")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    user_input = st.chat_input("Ask a question about the school database:")
    
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        with st.chat_message("assistant"):
            with st.spinner("Generating response..."):
                response = generate_response(user_input)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()