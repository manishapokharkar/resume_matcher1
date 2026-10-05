from candidate_parser import (
    parse_candidate,
    is_likely_resume
)

import os

folder = "email_resumes"

if not os.path.exists(folder):
    print("email_resumes folder does not exist.")
    exit()

for filename in os.listdir(folder):

    file_path = os.path.join(folder, filename)

    if not filename.lower().endswith((".pdf", ".docx")):
        continue

    print("\n================================")
    print("FILE:", filename)
    print("================================")

    try:
        candidate = parse_candidate(file_path)

        print("Name:", candidate["name"])
        print("Email:", candidate["email"])
        print("Phone:", candidate["phone"])
        print("Skills:", candidate["skills"])
        print("Experience:", candidate["experience"])
        print("Education:", candidate["education"])

        result = is_likely_resume(candidate)

        if result:
            print("\nRESULT: RESUME ✅")
        else:
            print("\nRESULT: NOT A RESUME ❌")

    except Exception as error:
        print("ERROR:", error)