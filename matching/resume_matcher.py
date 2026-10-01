import re


SKILLS = [
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


def extract_skills_from_jd(job_description):

    found_skills = []

    jd_lower = job_description.lower()

    for skill in SKILLS:

        if skill.lower() in jd_lower:

            found_skills.append(skill)

    return list(set(found_skills))


def calculate_match(candidate_skills, required_skills):

    candidate_lower = [
        skill.lower()
        for skill in candidate_skills
    ]

    matched = []
    missing = []

    for skill in required_skills:

        if skill.lower() in candidate_lower:

            matched.append(skill)

        else:

            missing.append(skill)

    if required_skills:

        score = (
            len(matched)
            / len(required_skills)
        ) * 100

    else:

        score = 0

    return {
        "score": round(score, 2),
        "matched_skills": matched,
        "missing_skills": missing
    }


def match_resume(candidate_skills, job_description):

    required_skills = extract_skills_from_jd(
        job_description
    )

    result = calculate_match(
        candidate_skills,
        required_skills
    )

    result["required_skills"] = required_skills

    return result