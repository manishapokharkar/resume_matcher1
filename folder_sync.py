import os

from candidate_parser import parse_candidate
from database.db import get_connection, create_table


# ============================================================
# ALLOWED RESUME FILE TYPES
# ============================================================

ALLOWED_EXTENSIONS = [".pdf", ".docx"]


# ============================================================
# CHECK IF FILE WAS ALREADY PROCESSED
# ============================================================

def already_processed(file_name):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM candidates
        WHERE resume_file = ?
        """,
        (file_name,)
    )

    result = cursor.fetchone()

    connection.close()

    return result is not None


# ============================================================
# SAVE CANDIDATE
# ============================================================

def save_candidate(candidate, file_name):

    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # Convert skills list to text
    # --------------------------------------------------------
    skills = candidate.get("skills", [])

    if isinstance(skills, list):

        skills = ", ".join(
            str(skill).strip()
            for skill in skills
            if skill
        )

    elif skills is None:

        skills = ""

    else:

        skills = str(skills)

    education = candidate.get("education", [])

    if isinstance(education, list):

        education = ", ".join(
            str(item).strip()
            for item in education
            if item
        )

    elif education is None:

        education = ""

    else:

        education = str(education)

    # --------------------------------------------------------
    # Resume text
    # --------------------------------------------------------
    resume_text = candidate.get(
        "resume_text",
        ""
    )

    if resume_text is None:
        resume_text = ""

    # Make sure resume_text is a string
    if not isinstance(resume_text, str):
        resume_text = str(resume_text)

    # --------------------------------------------------------
    # Insert candidate into database
    # --------------------------------------------------------
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
            resume_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            candidate.get("name"),
            candidate.get("email"),
            candidate.get("phone"),
            skills,
            candidate.get("experience"),
            education,
            file_name,
            resume_text
        )
    )

    connection.commit()
    connection.close()


# ============================================================
# SCAN RESUME FOLDER
# ============================================================

def scan_resume_folder(folder_path):

    # Make sure database table exists
    create_table()

    # --------------------------------------------------------
    # Check folder
    # --------------------------------------------------------

    if not os.path.exists(folder_path):

        raise FileNotFoundError(
            f"Folder not found: {folder_path}"
        )

    if not os.path.isdir(folder_path):

        raise ValueError(
            f"Path is not a folder: {folder_path}"
        )

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    files_checked = 0
    resumes_saved = 0
    already_processed_count = 0
    rejected_count = 0

    # --------------------------------------------------------
    # Start scan
    # --------------------------------------------------------

    print("=" * 60)
    print("LOCAL RESUME FOLDER SCAN")
    print("=" * 60)

    print(
        f"Folder: {folder_path}"
    )

    files = os.listdir(folder_path)

    print(
        f"Total files found: {len(files)}"
    )

    # ========================================================
    # PROCESS EACH FILE
    # ========================================================

    for file_name in files:

        file_path = os.path.join(
            folder_path,
            file_name
        )

        # ----------------------------------------------------
        # Ignore folders
        # ----------------------------------------------------

        if not os.path.isfile(file_path):

            continue

        # ----------------------------------------------------
        # Get extension
        # ----------------------------------------------------

        extension = os.path.splitext(
            file_name
        )[1].lower()

        # ----------------------------------------------------
        # Only PDF and DOCX
        # ----------------------------------------------------

        if extension not in ALLOWED_EXTENSIONS:

            print(
                f"Skipped unsupported file: "
                f"{file_name}"
            )

            continue

        files_checked += 1

        print()
        print("-" * 60)

        print(
            f"Checking: {file_name}"
        )

        # ====================================================
        # CHECK DUPLICATE
        # ====================================================

        if already_processed(file_name):

            already_processed_count += 1

            print(
                f"Already processed: "
                f"{file_name}"
            )

            continue

        # ====================================================
        # PARSE RESUME
        # ====================================================

        try:

            candidate = parse_candidate(
                file_path
            )

            print(
                f"Parsed name: "
                f"{candidate.get('name')}"
            )

            print(
                f"Parsed email: "
                f"{candidate.get('email')}"
            )

            # Debug information
            skills = candidate.get(
                "skills",
                []
            )

            print(
                f"Skills found: "
                f"{skills}"
            )

            resume_text = candidate.get(
                "resume_text",
                ""
            )

            print(
                f"Resume text length: "
                f"{len(resume_text)}"
            )

        except Exception as error:

            print(
                f"ERROR parsing "
                f"{file_name}: {error}"
            )

            rejected_count += 1

            continue

        # ====================================================
        # SAVE RESUME
        # ====================================================

        try:

            save_candidate(
                candidate,
                file_name
            )

            resumes_saved += 1

            print(
                f"SUCCESS - Resume saved: "
                f"{file_name}"
            )

        except Exception as error:

            print(
                f"ERROR saving "
                f"{file_name}: {error}"
            )

            rejected_count += 1

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print()
    print("=" * 60)
    print("FOLDER SCAN COMPLETED")
    print("=" * 60)

    print(
        f"Files checked: "
        f"{files_checked}"
    )

    print(
        f"New resumes: "
        f"{resumes_saved}"
    )

    print(
        f"Already processed: "
        f"{already_processed_count}"
    )

    print(
        f"Rejected: "
        f"{rejected_count}"
    )

    print("=" * 60)

    # ========================================================
    # RETURN REPORT TO STREAMLIT
    # ========================================================

    return {
        "files_checked": files_checked,
        "resumes_saved": resumes_saved,
        "already_processed": already_processed_count,
        "rejected_count": rejected_count
    }