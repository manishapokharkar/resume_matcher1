import sqlite3

DATABASE = "resume_matcher.db"


def get_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


def create_table():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT,

            email TEXT,

            phone TEXT,

            skills TEXT,

            experience TEXT,

            education TEXT,

            resume_file TEXT,

            resume_text TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    connection.commit()

    connection.close()


if __name__ == "__main__":

    create_table()

    print("Candidate database created successfully.")