# School Database Q&A Bot (GenAI Intern Assignment)

## Overview
This Retrieval-Augmented Generation (RAG) application, developed for the Fealty Technologies GenAI Intern Assignment, enables users to query a MySQL database (`school_db`) through a conversational chat interface and receive plain-English responses. Built with **LangChain**, **Google Gemini 1.5 Flash**, **MySQL**, and **Streamlit**, it supports queries about students, parents, marks, scholarships, classes, and more, with context-aware follow-up question handling.

## Features
- **Database Queries**: Retrieves data from `school_db` tables: `students`, `parents`, `subjects`, `scholarships`, `marks`, `bankdetails`, `classes`, `sections`.
- **Natural Language Interface**: Converts user questions (e.g., “Who are the parents of Riya Verma?”) into SQL queries and generates conversational responses.
- **Conversation Memory**: Supports follow-up questions using `ConversationBufferMemory`.
- **Security**: Sanitizes user inputs to prevent SQL injection.
- **Error Handling**: Manages Gemini API rate limits (`429` errors) and SQL syntax errors (`1064` errors).
- **Optimization**: Uses caching, database indexes, and query cleaning for performance.
- **Frontend**: Streamlit-based web interface for user interaction.

## Prerequisites
- **Python**: 3.8 or higher
- **MySQL Server**: 8.0 or compatible
- **Google API Key**: Obtain from [Google Cloud Console](https://console.cloud.google.com/)
- **MySQL Workbench**: For database management
- **Git**: For cloning the repository

## Setup Instructions
1. **Clone the Repository**:
 

2. **Set Up Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   Save the following as `requirements.txt`:
   ```text
   mysql-connector-python==8.0.33
   sqlalchemy==2.0.31
   langchain==0.3.0
   langchain-google-genai==2.1.8
   streamlit==1.37.0
   python-dotenv==1.0.1
   protobuf==4.25.3
   ```
   Install:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up MySQL Database**:
   - Create the `school_db` database:
     ```sql
     CREATE DATABASE school_db;
     ```
   - Import the provided SQL files (assumed to be `school_db_*.sql`):
     ```bash
     mysql -u your_username -p school_db < school_db_students.sql
     mysql -u your_username -p school_db < school_db_parents.sql
     mysql -u your_username -p school_db < school_db_subjects.sql
     mysql -u your_username -p school_db < school_db_scholarships.sql
     mysql -u your_username -p school_db < school_db_marks.sql
     mysql -u your_username -p school_db < school_db_bankdetails.sql
     mysql -u your_username -p school_db < school_db_classes.sql
     mysql -u your_username -p school_db < school_db_sections.sql
     ```
   - Verify tables:
     ```sql
     USE school_db;
     SHOW TABLES;
     ```
     Expected output:
     ```
     +------------------+
     | Tables_in_school_db |
     +------------------+
     | bankdetails      |
     | classes          |
     | marks            |
     | parents          |
     | scholarships     |
     | sections         |
     | students         |
     | subjects         |
     +------------------+
     ```

5. **Set Up Environment Variables**:
   - Create a `.env` file in the project root:
     ```text
     MYSQL_USER=your_username
     MYSQL_PASSWORD=your_password
     MYSQL_HOST=localhost
     MYSQL_DATABASE=school_db
     GOOGLE_API_KEY=your_google_api_key
     ```
   - Replace `your_username`, `your_password`, and `your_google_api_key` with your credentials.

6. **Run the Application**:
   ```bash
   streamlit run app.py
   ```
   - Open `http://localhost:8501` in your browser.

## Testing
Test the application with the following queries:
- **Query**: “Who are the parents of Riya Verma?”
  - **Expected Response**: “Riya Verma's parents are Mrs. Sunita Verma (Mother) and Mr. Rajesh Verma (Father).”
- **Query**: “What are the marks of student roll number 101?”
  - **Expected Response**: “Student roll number 101 scored 88.50 in Mathematics and 92.00 in English.”
- **Query**: “Which students have a Merit Scholarship?”
  - **Expected Response**: “Riya Verma and Pooja Kumar have a Merit Scholarship.”
- **Query**: “List students in Grade 10, Section A.”
  - **Expected Response**: “Riya Verma is in Grade 10, Section A.”
- **Follow-up Query**: “What is her bank account number?”
  - **Expected Response**: “Riya Verma's bank account number is SBIN0001234 with State Bank of India.”

Check `app.log` for debugging information on SQL queries, rate limits, or errors.

## Project Structure
```
<repo-directory>/
├── app.py              # Main application script
├── requirements.txt    # Python dependencies
├── .env                # Environment variables
├── app.log             # Log file for debugging(After running)
└── README.md           # This file
```

## Design Choices
- **LangChain**: Powers the RAG pipeline with `create_sql_query_chain` and `ConversationBufferMemory`.
- **Gemini 1.5 Flash**: Chosen for higher rate limits and cost-effectiveness compared to `gemini-1.5-pro`.
- **Streamlit**: Provides a user-friendly chat interface.
- **Error Handling**: Manages Gemini API rate limits (`429`), SQL syntax errors (`1064`), and prompt validation errors.
- **Optimization**: Uses caching (`lru_cache`), database indexes, and query cleaning for performance.
- **Security**: Sanitizes user inputs to prevent SQL injection.

## Troubleshooting
- **Gemini API Rate Limits**:
  - Wait 6-10 seconds between queries or request a quota increase: https://console.cloud.google.com/quotas
  - Verify `GOOGLE_API_KEY` in `.env`.
- **SQL Errors (1064)**:
  - Check `app.log` for the failing query.
  - Test queries in MySQL Workbench, e.g.:
    ```sql
    SELECT marks_obtained FROM marks WHERE student_roll_no = 101 LIMIT 5;
    ```
- **Dependency Conflicts**:
  - Recreate virtual environment:
    ```bash
    rm -rf venv  # On Windows: rmdir /s venv
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
- **Database Issues**:
  - Ensure `school_db` is imported correctly.
  - Verify table structure:
    ```sql
    DESCRIBE students;
    ```
