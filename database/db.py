import sqlite3
import os


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DATABASE = "resume_matcher.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Create and return a SQLite database connection.
    """

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# CREATE / UPDATE DATABASE
# ============================================================

def create_table():
    """
    Create the candidates table if it doesn't exist.

    Also performs a lightweight database migration for
    existing databases so newly added columns are created
    automatically.
    """

    connection = get_connection()

    cursor = connection.cursor()

    # --------------------------------------------------------
    # Create candidates table if it does not exist
    # --------------------------------------------------------

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

            source TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)

    # --------------------------------------------------------
    # Check existing columns
    # --------------------------------------------------------

    cursor.execute("""
        PRAGMA table_info(candidates)
    """)

    existing_columns = {
        row[1]
        for row in cursor.fetchall()
    }

    # --------------------------------------------------------
    # Add source column to older databases
    # --------------------------------------------------------

    if "source" not in existing_columns:

        cursor.execute("""
            ALTER TABLE candidates
            ADD COLUMN source TEXT
        """)

    # --------------------------------------------------------
    # Commit changes
    # --------------------------------------------------------

    connection.commit()

    connection.close()


# ============================================================
# INITIALIZE DATABASE
# ============================================================

create_table()


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    print("Checking database...")

    create_table()

    print("Candidate database is ready.")

    print(f"Database file: {os.path.abspath(DATABASE)}")