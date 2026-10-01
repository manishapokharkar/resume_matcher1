from database.db import get_connection


connection = get_connection()

cursor = connection.cursor()

cursor.execute("""
    SELECT
        id,
        name,
        email,
        phone,
        skills,
        experience,
        education,
        resume_file,
        created_at
    FROM candidates
""")

candidates = cursor.fetchall()

print("\nCandidates in database:\n")

for candidate in candidates:

    print("--------------------------------")
    print("ID:", candidate["id"])
    print("Name:", candidate["name"])
    print("Email:", candidate["email"])
    print("Phone:", candidate["phone"])
    print("Skills:", candidate["skills"])
    print("Experience:", candidate["experience"])
    print("Education:", candidate["education"])
    print("Resume:", candidate["resume_file"])

connection.close()