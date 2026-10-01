import os

from candidate_parser import parse_candidate
from database.db import get_connection, create_table


def save_candidate(candidate, resume_file):

    connection = get_connection()

    cursor = connection.cursor()

    skills = ", ".join(candidate["skills"])

    education = ", ".join(candidate["education"])

    cursor.execute("""
        INSERT INTO candidates (
            name,
            email,
            phone,
            skills,
            experience,
            education,
            resume_file,
            resume_text
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        candidate["name"],
        candidate["email"],
        candidate["phone"],
        skills,
        candidate["experience"],
        education,
        resume_file,
        candidate["resume_text"]

    ))

    connection.commit()

    connection.close()


def process_resumes():

    create_table()

    folder = "email_resumes"

    for filename in os.listdir(folder):

        if not filename.lower().endswith(
            (".pdf", ".docx")
        ):
            continue

        file_path = os.path.join(
            folder,
            filename
        )

        print("\nProcessing:", filename)

        candidate = parse_candidate(
            file_path
        )

        save_candidate(
            candidate,
            filename
        )

        print(
            "Saved candidate:",
            candidate["name"]
        )


if __name__ == "__main__":

    process_resumes()

    print("\nAll candidates saved successfully.")