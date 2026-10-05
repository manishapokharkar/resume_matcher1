from candidate_parser import is_likely_resume
from database.db import create_table, get_connection
from matching.resume_matcher import match_resume


def get_candidates():

    create_table()
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
            resume_text
        FROM candidates
    """)

    candidates = cursor.fetchall()

    connection.close()

    return candidates


def convert_skills(skills_text):

    if not skills_text:
        return []

    return [
        skill.strip()
        for skill in skills_text.split(",")
    ]


def match_candidates(job_description):

    candidates = get_candidates()

    results = []

    for candidate in candidates:

        if not is_likely_resume(dict(candidate)):
            continue

        candidate_skills = convert_skills(
            candidate["skills"]
        )

        match = match_resume(
            candidate_skills,
            job_description
        )

        results.append({
            "id": candidate["id"],
            "name": candidate["name"],
            "email": candidate["email"],
            "skills": candidate["skills"],
            "experience": candidate["experience"],
            "score": match["score"],
            "matched_skills": ", ".join(
                match["matched_skills"]
            ),
            "missing_skills": ", ".join(
                match["missing_skills"]
            )
        })

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return results


if __name__ == "__main__":

    job_description = """
    Frontend Developer

    We are looking for a developer with:

    React
    JavaScript
    Next.js
    Tailwind CSS
    Git
    """

    results = match_candidates(
        job_description
    )

    print("\nCandidate Matching Results\n")

    for result in results:

        print("--------------------------------")
        print("Name:", result["name"])
        print("Email:", result["email"])
        print("Experience:", result["experience"])
        print("Score:", result["score"], "%")
        print(
            "Matched:",
            result["matched_skills"]
        )
        print(
            "Missing:",
            result["missing_skills"]
        )