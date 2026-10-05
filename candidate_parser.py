import re

from resume_file_parser import extract_resume_text


# ============================================================
# EMAIL
# ============================================================

def extract_email(text):

    match = re.search(
        r'[\w\.-]+@[\w\.-]+\.\w+',
        text
    )

    if match:
        return match.group(0)

    return ""


# ============================================================
# PHONE
# ============================================================

def extract_phone(text):

    patterns = [
        r'(?:\+91[\s-]?)?[6-9]\d{9}',
        r'\+?\d[\d\s-]{8,14}\d'
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:
            return match.group(0).strip()

    return ""


# ============================================================
# NAME
# ============================================================

def extract_name(text):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    ignored_words = [
        "resume",
        "curriculum vitae",
        "curriculum",
        "vitae",
        "cv",
        "profile",
        "email",
        "phone",
        "mobile",
        "contact",
        "address"
    ]

    for line in lines[:20]:

        line_lower = line.lower()

        if any(
            word in line_lower
            for word in ignored_words
        ):
            continue

        if "@" in line:
            continue

        if re.search(
            r'\d{7,}',
            line
        ):
            continue

        if len(line) > 60:
            continue

        if len(
            re.findall(
                r'[^a-zA-Z .]',
                line
            )
        ) > 3:
            continue

        words = line.split()

        if 2 <= len(words) <= 5:
            return line

    return ""


# ============================================================
# SKILLS
# ============================================================

def extract_skills(text):

    common_skills = [

        # ----------------------------------------------------
        # SOFTWARE / IT
        # ----------------------------------------------------

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
        "Azure",
        "Docker",
        "Git",
        "REST API",
        "REST APIs",
        "Figma",
        "Selenium",
        "Jenkins",

        # ----------------------------------------------------
        # PROCESS / CHEMICAL ENGINEERING
        # ----------------------------------------------------

        "Piping",
        "Piping Line List",
        "Piping Design",
        "Process Engineering",
        "Chemical Engineering",
        "Process Design",
        "Process Calculations",

        # ----------------------------------------------------
        # VALVES
        # ----------------------------------------------------

        "Valves",
        "Control Valves",
        "Control Valve Sizing",
        "Valve Sizing",
        "Valve Applications",
        "Breather Valves",
        "Pressure Relief Valves",
        "PSV",
        "PRV",
        "RD",
        "Rupture Disc",

        # ----------------------------------------------------
        # PUMPS
        # ----------------------------------------------------

        "Pumps",
        "Pump Calculations",
        "Pump Sizing",
        "Pump Datasheet",

        # ----------------------------------------------------
        # EQUIPMENT
        # ----------------------------------------------------

        "Heat Exchangers",
        "Heat Exchanger Design",
        "Cooling Tower",
        "Storage Tanks",
        "Tank Design",
        "Equipment Design",
        "Equipment Datasheet",
        "Process Datasheet",
        "Instrument Process Datasheet",

        # ----------------------------------------------------
        # PIPING / PROCESS DOCUMENTS
        # ----------------------------------------------------

        "BFD",
        "Block Flow Diagram",
        "PFD",
        "Process Flow Diagram",
        "UFD",
        "Utility Flow Diagram",
        "P&ID",
        "Piping and Instrumentation Diagram",

        # ----------------------------------------------------
        # SAFETY / RELIEF
        # ----------------------------------------------------

        "Hazardous Area Classification",
        "HAC",
        "Relief Events",
        "Pressure Setting",
        "Pressure Setting Criteria",
        "Relief Valve",
        "Venting",
        "Venting Requirements",

        # ----------------------------------------------------
        # INDUSTRY STANDARDS
        # ----------------------------------------------------

        "API 2000",
        "GPSA",
        "API",
        "ASME",
        "ANSI",
        "ASTM",
        "NFPA",
        "IEC",
        "ISO",

        # ----------------------------------------------------
        # OTHER PROCESS ENGINEERING
        # ----------------------------------------------------

        "Air Moisture Separator",
        "Separator Calculations",
        "Moisture Separator",
        "Process Equipment",
        "Process Datasheets",
        "Instrument Datasheets",
        "Chemical Process",
        "Process Industry",
        "Chemical Industry"
    ]

    found_skills = []

    text_lower = text.lower()

    for skill in common_skills:

        if skill.lower() in text_lower:

            if skill not in found_skills:

                found_skills.append(skill)

    return found_skills


# ============================================================
# EXPERIENCE
# ============================================================

def extract_experience(text):

    patterns = [

        r'(\d+(?:\.\d+)?)\+?\s*years?\s*(?:of)?\s*experience',

        r'(\d+(?:\.\d+)?)\+?\s*years?\s*exp',

        r'(\d+(?:\.\d+)?)\+?\s*yrs?\s*(?:of)?\s*experience'
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return (
                match.group(1)
                + " years"
            )

    return ""


# ============================================================
# EDUCATION
# ============================================================

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
        "MBA",
        "Bachelor's",
        "Master's",

        # Engineering
        "Chemical Engineering",
        "Mechanical Engineering",
        "Civil Engineering",
        "Electrical Engineering",
        "Instrumentation Engineering",
        "Process Engineering"
    ]

    found = []

    text_lower = text.lower()

    for education in education_keywords:

        if education.lower() in text_lower:

            if education not in found:

                found.append(education)

    return found


# ============================================================
# PARSE CANDIDATE
# ============================================================

def parse_candidate(file_path):

    text = extract_resume_text(
        file_path
    )

    candidate = {

        "name": extract_name(text),

        "email": extract_email(text),

        "phone": extract_phone(text),

        "skills": extract_skills(text),

        "experience": extract_experience(text),

        "education": extract_education(text),

        # IMPORTANT:
        # Keep the COMPLETE resume text
        "resume_text": text
    }

    return candidate


# ============================================================
# RESUME DETECTION
# ============================================================

def is_likely_resume(candidate):

    text = candidate.get(
        "resume_text",
        ""
    )

    text_lower = text.lower()

    score = 0

    # --------------------------------------------------------
    # Basic candidate information
    # --------------------------------------------------------

    if candidate.get("name"):
        score += 2

    if candidate.get("email"):
        score += 2

    if candidate.get("phone"):
        score += 1

    # --------------------------------------------------------
    # Skills
    # --------------------------------------------------------

    skills = candidate.get(
        "skills",
        []
    )

    if len(skills) >= 1:
        score += 2

    if len(skills) >= 3:
        score += 1

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    if candidate.get("experience"):
        score += 2

    # --------------------------------------------------------
    # Education
    # --------------------------------------------------------

    if candidate.get("education"):
        score += 2

    # --------------------------------------------------------
    # Resume sections
    # --------------------------------------------------------

    resume_sections = [

        "experience",
        "work experience",
        "professional experience",
        "employment",

        "education",

        "skills",
        "technical skills",

        "projects",

        "certifications",

        "objective",
        "summary",
        "professional summary",
        "career objective",

        "achievements",
        "responsibilities",

        # Engineering resume sections
        "professional experience",
        "technical experience",
        "process engineering",
        "engineering experience",
        "design experience",
        "process design",
        "piping",
        "projects"
    ]

    section_count = 0

    for section in resume_sections:

        if section in text_lower:

            section_count += 1

    if section_count >= 1:
        score += 2

    if section_count >= 3:
        score += 2

    # --------------------------------------------------------
    # Job-related words
    # --------------------------------------------------------

    job_terms = [

        # IT
        "developer",
        "engineer",
        "analyst",
        "designer",
        "manager",
        "consultant",
        "intern",
        "software",
        "frontend",
        "backend",
        "full stack",
        "full-stack",
        "data analyst",
        "web developer",
        "programmer",
        "technology",
        "technical",

        # Engineering
        "process engineer",
        "process engineering",
        "chemical engineer",
        "chemical engineering",
        "mechanical engineer",
        "piping engineer",
        "design engineer",
        "process design",
        "plant design",
        "engineering"
    ]

    for term in job_terms:

        if term in text_lower:

            score += 2

            break

    # --------------------------------------------------------
    # Minimum text length
    # --------------------------------------------------------

    if len(text.strip()) >= 300:

        score += 1

    # --------------------------------------------------------
    # Final decision
    # --------------------------------------------------------

    return score >= 5