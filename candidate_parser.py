import re
from resume_file_parser import extract_resume_text


def extract_email(text):
    match = re.search(
        r'[\w\.-]+@[\w\.-]+\.\w+',
        text
    )

    return match.group(0) if match else ""


def extract_phone(text):
    match = re.search(
        r'(?:\+91[\s-]?)?[6-9]\d{9}',
        text
    )

    return match.group(0) if match else ""


def extract_name(text):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # Usually the candidate name is near the top
    for line in lines[:10]:

        if (
            "resume" not in line.lower()
            and "curriculum vitae" not in line.lower()
            and "cv" != line.lower()
            and "email" not in line.lower()
            and "phone" not in line.lower()
        ):

            # Avoid lines that are clearly contact information
            if not re.search(r'@|\d{7,}', line):
                return line

    return ""


def extract_skills(text):

    common_skills = [
        "Python",
        "Java",
        "JavaScript",
        "TypeScript",
        "React",
        "React.js",
        "Next.js",
        "Angular",
        "Vue.js",
        "HTML",
        "CSS",
        "Tailwind CSS",
        "Bootstrap",
        "Node.js",
        "Express",
        "Django",
        "Flask",
        "FastAPI",
        "PHP",
        "WordPress",
        "MySQL",
        "PostgreSQL",
        "MongoDB",
        "SQL",
        "Power BI",
        "Excel",
        "Snowflake",
        "dbt",
        "AWS",
        "Docker",
        "Git"
    ]

    found_skills = []

    text_lower = text.lower()

    for skill in common_skills:

        if skill.lower() in text_lower:
            found_skills.append(skill)

    return found_skills


def extract_experience(text):

    patterns = [
        r'(\d+(?:\.\d+)?)\+?\s*years?\s*(?:of)?\s*experience',
        r'(\d+(?:\.\d+)?)\+?\s*years?\s*exp'
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1) + " years"

    return ""


def extract_education(text):

    education_keywords = [
        "Bachelor",
        "B.Tech",
        "B.E.",
        "BCA",
        "B.Sc",
        "Master",
        "M.Tech",
        "MCA",
        "M.Sc",
        "MBA"
    ]

    found = []

    for education in education_keywords:

        if education.lower() in text.lower():
            found.append(education)

    return found


def parse_candidate(file_path):

    text = extract_resume_text(file_path)

    candidate = {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text),
        "experience": extract_experience(text),
        "education": extract_education(text),
        "resume_text": text
    }

    return candidate


if __name__ == "__main__":

    import os

    folder = "email_resumes"

    for filename in os.listdir(folder):

        file_path = os.path.join(
            folder,
            filename
        )

        if filename.lower().endswith(
            (".pdf", ".docx")
        ):

            print("\n================================")
            print("FILE:", filename)
            print("================================")

            candidate = parse_candidate(
                file_path
            )

            print("\nName:")
            print(candidate["name"])

            print("\nEmail:")
            print(candidate["email"])

            print("\nPhone:")
            print(candidate["phone"])

            print("\nSkills:")
            print(", ".join(candidate["skills"]))

            print("\nExperience:")
            print(candidate["experience"])

            print("\nEducation:")
            print(", ".join(candidate["education"]))