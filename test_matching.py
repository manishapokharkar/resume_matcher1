from matching.resume_matcher import match_resume


candidate_skills = [
    "React",
    "JavaScript",
    "HTML",
    "CSS",
    "Git"
]


job_description = """
We are looking for a Frontend Developer.

Required skills:

React
JavaScript
Next.js
Tailwind CSS
Git
"""


result = match_resume(
    candidate_skills,
    job_description
)


print("\nRequired Skills:")
print(result["required_skills"])

print("\nMatched Skills:")
print(result["matched_skills"])

print("\nMissing Skills:")
print(result["missing_skills"])

print("\nMatch Score:")
print(str(result["score"]) + "%")