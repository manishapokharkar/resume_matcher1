import sqlite3
from pathlib import Path


# ============================================================
# DATABASE LOCATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE = BASE_DIR / "resume_matcher.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Create and return a SQLite database connection.
    """

    connection = sqlite3.connect(
        DATABASE,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# CREATE / UPDATE DATABASE TABLE
# ============================================================

def create_table():
    """
    Create the candidates table if it does not exist.

    Also adds the 'source' column to older databases
    that were created before source tracking was added.
    """

    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # Create table
    # --------------------------------------------------------

    cursor.execute(
        """
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

            source TEXT DEFAULT 'email',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    # --------------------------------------------------------
    # Check existing columns
    # --------------------------------------------------------

    cursor.execute(
        "PRAGMA table_info(candidates)"
    )

    columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    # --------------------------------------------------------
    # Add source column to old database
    # --------------------------------------------------------

    if "source" not in columns:

        cursor.execute(
            """
            ALTER TABLE candidates
            ADD COLUMN source TEXT DEFAULT 'email'
            """
        )

    # --------------------------------------------------------
    # Add created_at if an older database doesn't have it
    # --------------------------------------------------------

    if "created_at" not in columns:

        cursor.execute(
            """
            ALTER TABLE candidates
            ADD COLUMN created_at
            TIMESTAMP
            """
        )

    connection.commit()
    connection.close()


# ============================================================
# INSERT CANDIDATE
# ============================================================

def insert_candidate(
    name,
    email,
    phone,
    skills,
    experience,
    education,
    resume_file,
    resume_text,
    source="email"
):
    """
    Insert one candidate into the database.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO candidates
        (
            name,
            email,
            phone,
            skills,
            experience,
            education,
            resume_file,
            resume_text,
            source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            email,
            phone,
            skills,
            experience,
            education,
            resume_file,
            resume_text,
            source
        )
    )

    connection.commit()

    candidate_id = cursor.lastrowid

    connection.close()

    return candidate_id


# ============================================================
# GET ALL CANDIDATES
# ============================================================

def get_all_candidates():

    create_table()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM candidates
        ORDER BY created_at DESC, id DESC
        """
    )

    candidates = cursor.fetchall()

    connection.close()

    return candidates


# ============================================================
# GET CANDIDATE BY ID
# ============================================================

def get_candidate_by_id(candidate_id):

    create_table()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM candidates
        WHERE id = ?
        """,
        (candidate_id,)
    )

    candidate = cursor.fetchone()

    connection.close()

    return candidate


# ============================================================
# CHECK DUPLICATE CANDIDATE
# ============================================================

def candidate_exists(
    email=None,
    resume_file=None
):
    """
    Check whether a candidate/resume is already stored.

    Email is checked first when available.
    Resume filename is checked as a fallback.
    """

    create_table()

    connection = get_connection()
    cursor = connection.cursor()

    try:

        if email:

            cursor.execute(
                """
                SELECT id
                FROM candidates
                WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))
                LIMIT 1
                """,
                (email,)
            )

        elif resume_file:

            cursor.execute(
                """
                SELECT id
                FROM candidates
                WHERE LOWER(TRIM(resume_file)) = LOWER(TRIM(?))
                LIMIT 1
                """,
                (resume_file,)
            )

        else:

            return False

        result = cursor.fetchone()

        return result is not None

    finally:

        connection.close()


# ============================================================
# DELETE CANDIDATE
# ============================================================

def delete_candidate(candidate_id):

    create_table()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM candidates
        WHERE id = ?
        """,
        (candidate_id,)
    )

    connection.commit()

    connection.close()


# ============================================================
# COUNT CANDIDATES
# ============================================================

def count_candidates():

    create_table()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM candidates
        """
    )

    result = cursor.fetchone()

    connection.close()

    return result["total"]


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

create_table()