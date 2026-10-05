import re

from database.db import create_table, get_connection
from matching.resume_matcher import match_resume


# ============================================================
# GET ALL CANDIDATES
# ============================================================

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
        ORDER BY id DESC
    """)

    candidates = cursor.fetchall()

    connection.close()

    return candidates


# ============================================================
# CONVERT SKILLS TEXT INTO LIST
# ============================================================

def convert_skills(skills_text):

    if not skills_text:
        return []

    return [
        skill.strip()
        for skill in skills_text.split(",")
        if skill.strip()
    ]


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = text.lower()

    # Normalize common variations
    text = text.replace(
        "piping & instrumentation diagram",
        "p&id"
    )

    text = text.replace(
        "piping and instrumentation diagram",
        "p&id"
    )

    text = text.replace(
        "process flow diagram",
        "pfd"
    )

    text = text.replace(
        "block flow diagram",
        "bfd"
    )

    text = text.replace(
        "utility flow diagram",
        "ufd"
    )

    text = re.sub(
        r'\s+',
        ' ',
        text
    )

    return text.strip()


# ============================================================
# EXTRACT IMPORTANT JD TERMS
# ============================================================

def extract_jd_terms(job_description):

    normalized_jd = normalize_text(
        job_description
    )

    # Important engineering / technical phrases
    important_terms = [

        "piping line list",
        "piping",
        "valves",
        "control valves",
        "control valve",
        "pump calculations",
        "pump sizing",
        "pump datasheet",
        "control valve sizing",
        "heat exchanger",
        "heat exchangers",
        "cooling tower",
        "breather valves",
        "breather valve",
        "api 2000",
        "storage tanks",
        "storage tank",
        "hazardous area classification",
        "hac",
        "bfd",
        "pfd",
        "ufd",
        "p&id",
        "equipment process datasheet",
        "instrument process datasheet",
        "equipment datasheet",
        "instrument datasheet",
        "psv",
        "prv",
        "rupture disc",
        "rd",
        "pressure setting",
        "pressure setting criteria",
        "relief events",
        "air moisture separator",
        "gpsa",
        "process industry",
        "chemical industry",
        "process engineering",
        "chemical engineering",
        "process design",
        "process calculations",
        "piping design",
        "valve sizing",
        "pump design",
        "heat exchanger design",
        "tank design"
    ]

    found_terms = []

    for term in important_terms:

        if term in normalized_jd:

            if term not in found_terms:

                found_terms.append(term)

    # --------------------------------------------------------
    # Also look for normal words from JD
    # --------------------------------------------------------

    stop_words = {

        "the",
        "and",
        "for",
        "with",
        "about",
        "know",
        "knowledge",
        "types",
        "applications",
        "design",
        "requirements",
        "used",
        "industry",
        "relevant",
        "as",
        "per",
        "of",
        "to",
        "in",
        "on",
        "a",
        "an",
        "is",
        "are",
        "be",
        "this",
        "that"
    }

    words = re.findall(
        r'\b[a-zA-Z0-9&]+\b',
        normalized_jd
    )

    for word in words:

        if len(word) < 3:
            continue

        if word in stop_words:
            continue

        if word not in found_terms:

            found_terms.append(word)

    return found_terms


# ============================================================
# CALCULATE FULL RESUME TEXT MATCH
# ============================================================

def calculate_text_match(
    resume_text,
    job_description
):

    resume_text = normalize_text(
        resume_text
    )

    jd_terms = extract_jd_terms(
        job_description
    )

    if not resume_text or not jd_terms:

        return {
            "score": 0,
            "matched": [],
            "missing": []
        }

    matched = []
    missing = []

    for term in jd_terms:

        if term.lower() in resume_text:

            matched.append(term)

        else:

            missing.append(term)

    score = (
        len(matched) /
        len(jd_terms)
    ) * 100

    return {
        "score": round(score),
        "matched": matched,
        "missing": missing
    }


# ============================================================
# MATCH CANDIDATES
# ============================================================

def match_candidates(job_description):

    candidates = get_candidates()

    results = []

    # --------------------------------------------------------
    # Validate JD
    # --------------------------------------------------------

    if not job_description:

        return []

    # --------------------------------------------------------
    # Process every candidate
    # --------------------------------------------------------

    for candidate in candidates:

        candidate_skills = convert_skills(
            candidate["skills"]
        )

        # ----------------------------------------------------
        # Existing skill-based matching
        # ----------------------------------------------------

        skill_match = match_resume(
            candidate_skills,
            job_description
        )

        skill_score = skill_match.get(
            "score",
            0
        )

        # ----------------------------------------------------
        # Full resume text matching
        # ----------------------------------------------------

        text_match = calculate_text_match(
            candidate["resume_text"],
            job_description
        )

        text_score = text_match["score"]

        # ----------------------------------------------------
        # Combined score
        #
        # 40% extracted skills
        # 60% actual resume text
        # ----------------------------------------------------

        combined_score = round(
            (
                skill_score * 0.40
            )
            +
            (
                text_score * 0.60
            )
        )

        # ----------------------------------------------------
        # Combine matched skills/terms
        # ----------------------------------------------------

        matched_items = []

        for item in skill_match.get(
            "matched_skills",
            []
        ):

            if item not in matched_items:

                matched_items.append(item)

        for item in text_match.get(
            "matched",
            []
        ):

            if item not in matched_items:

                matched_items.append(item)

        # ----------------------------------------------------
        # Combine missing terms
        # ----------------------------------------------------

        missing_items = []

        for item in skill_match.get(
            "missing_skills",
            []
        ):

            if item not in missing_items:

                missing_items.append(item)

        for item in text_match.get(
            "missing",
            []
        ):

            if item not in missing_items:

                missing_items.append(item)

        # ----------------------------------------------------
        # Store result
        # ----------------------------------------------------

        results.append({

            "id": candidate["id"],

            "name": candidate["name"],

            "email": candidate["email"],

            "phone": candidate["phone"],

            "skills": candidate["skills"],

            "experience": candidate["experience"],

            "education": candidate["education"],

            "resume_file": candidate["resume_file"],

            "score": combined_score,

            "matched_skills": ", ".join(
                matched_items
            ),

            "missing_skills": ", ".join(
                missing_items
            ),

            "skill_score": skill_score,

            "text_score": text_score
        })

    # --------------------------------------------------------
    # Highest score first
    # --------------------------------------------------------

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return results