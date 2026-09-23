"""
Resume Screening and Matching Assistant
Stack: Streamlit, LangChain, Llama 3 (Groq), MiniLM Embeddings, Chroma DB,
       PyPDFLoader, BeautifulSoup + Requests
"""

import os
import re
import tempfile
import uuid
import zipfile
from io import BytesIO
from typing import Any, List, TypedDict

import requests
import streamlit as st
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
URL_RE = re.compile(r"https?://[^\s)>\]]+")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading embedding model (first run downloads it)...")
def get_embeddings():
    """Load a lightweight local embedding model for resume retrieval."""
    from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def scrape_url(url: str, max_chars: int = 4000) -> str:
    """Fetch a web page with Requests and extract readable text with BeautifulSoup."""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except requests.RequestException:
        return ""
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())[:max_chars]


# --------------------------------------------------------------------------
# Matching workflow
# --------------------------------------------------------------------------
class MatchState(TypedDict, total=False):
    resume_path: str
    jd_text: str
    resume_text: str
    resume_chunks: List[Any]
    jd_full: str
    vectorstore: Any
    context: str
    result: dict


def load_resume(state: MatchState) -> MatchState:
    docs = PyPDFLoader(state["resume_path"]).load()
    text = "\n".join(d.page_content for d in docs).strip()
    if not text:
        raise ValueError("No text could be extracted from the PDF (is it a scanned image?).")
    return {"resume_text": text, "resume_chunks": docs}


def parse_job_description(state: MatchState) -> MatchState:
    jd = state["jd_text"]
    extra = []
    for url in URL_RE.findall(jd)[:3]:
        page = scrape_url(url)
        if page:
            extra.append(f"[Content from {url}]\n{page}")
    return {"jd_full": jd + ("\n\n" + "\n\n".join(extra) if extra else "")}


def index_resume(state: MatchState) -> MatchState:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)
    chunks = splitter.split_documents(state["resume_chunks"])
    vs = Chroma.from_documents(
        chunks,
        embedding=get_embeddings(),
        collection_name=f"resume_{uuid.uuid4().hex[:12]}",
    )
    return {"vectorstore": vs}


def retrieve_context(state: MatchState) -> MatchState:
    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=30)
    queries = splitter.split_text(state["jd_full"])
    seen, passages = set(), []
    for q in queries:
        for doc in state["vectorstore"].similarity_search(q, k=2):
            if doc.page_content not in seen:
                seen.add(doc.page_content)
                passages.append(doc.page_content)
    header = state["resume_text"][:800]
    return {"context": f"[Resume header]\n{header}\n\n[Relevant resume sections]\n" + "\n---\n".join(passages)}


PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert technical recruiter. Compare the candidate's resume "
            "against the job description. Be objective and only use evidence from the resume. "
            "Respond with ONLY valid JSON, no markdown, using exactly these keys:\n"
            '{{"match_score": <integer 0-100>, "summary": "<2-3 sentences>", '
            '"matched_skills": ["..."], "missing_skills": ["..."], '
            '"strengths": ["..."], "concerns": ["..."], '
            '"recommendation": "Strong Match" | "Moderate Match" | "Weak Match"}}',
        ),
        ("human", "JOB DESCRIPTION:\n{jd}\n\nRESUME EXCERPTS:\n{context}"),
    ]
)


def analyze_match(state: MatchState) -> MatchState:
    llm = ChatGroq(model=GROQ_MODEL, temperature=0, api_key=os.getenv("GROQ_API_KEY"))
    chain = PROMPT | llm | JsonOutputParser()
    result = chain.invoke({"jd": state["jd_full"][:8000], "context": state["context"]})
    return {"result": result}


# --------------------------------------------------------------------------
# UI helpers
# --------------------------------------------------------------------------
REC_STYLE = {
    "Strong Match": {"color": "#1a7f37", "bg": "#e8f7ee", "icon": "🟢"},
    "Moderate Match": {"color": "#9a6700", "bg": "#fff6e0", "icon": "🟡"},
    "Weak Match": {"color": "#c0362c", "bg": "#fdecea", "icon": "🔴"},
}


def score_color(score: int) -> str:
    if score >= 75:
        return "#1a7f37"
    if score >= 50:
        return "#9a6700"
    return "#c0362c"


def inject_css():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

            :root {
                --ink: #17232d;
                --muted: #69767d;
                --line: #dce4e1;
                --paper: #f4f7f5;
                --surface: #ffffff;
                --teal: #237d78;
                --coral: #dc654c;
            }

            .main > div { padding-top: 0.25rem; }
            #MainMenu, footer { visibility: hidden; }
            .stApp,
            section[data-testid="stMain"],
            .main { background: #ffffff; color: var(--ink); }
            body, p, label, button, input { font-family: 'DM Sans', sans-serif; }
            h1, h2, h3, h4, [data-testid="stMetricValue"] {
                font-family: 'Space Grotesk', sans-serif;
                color: var(--ink);
            }

            .app-hero {
                background: linear-gradient(120deg, #173a43 0%, #236e70 58%, #d66a50 150%);
                padding: 30px 32px 28px;
                border-radius: 10px;
                margin-bottom: 16px;
                box-shadow: 0 8px 24px rgba(23, 58, 67, 0.16);
                position: relative;
                overflow: hidden;
            }
            .app-hero h1 {
                color: #ffffff;
                margin: 0;
                font: 700 clamp(1.7rem, 4vw, 2.6rem)/1.05 'Space Grotesk', sans-serif;
                letter-spacing: -0.03em;
                max-width: 660px;
                text-align: left;
            }
            .app-hero h1::first-line { color: #ffffff; }
            .app-hero p {
                color: #d9eeea;
                margin: 10px 0 0;
                font-size: 0.98rem;
                line-height: 1.5;
                max-width: 600px;
                text-align: left;
            }

            .sidebar-title {
                color: var(--coral);
                font: 700 0.72rem 'DM Sans', sans-serif;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                margin-bottom: 0.25rem;
            }
            .sidebar-subtitle {
                color: var(--muted);
                font-size: 0.86rem;
                line-height: 1.45;
                margin-bottom: 1rem;
            }

            .result-heading {
                border-top: 3px solid var(--ink);
                padding-top: 0.7rem;
                margin-top: 1.2rem;
            }
            .result-heading p {
                color: var(--muted);
                margin-top: -0.5rem;
            }

            .empty-state {
                background: var(--surface);
                border: 1px dashed #b8c8c3;
                border-radius: 10px;
                color: var(--muted);
                margin-top: 1.5rem;
                padding: 36px 24px;
                text-align: center;
            }
            .empty-state strong { color: var(--ink); }

            [data-testid="stMetric"] {
                background: var(--surface);
                border: 1px solid var(--line);
                border-left: 4px solid var(--teal);
                border-radius: 7px;
                padding: 0.7rem 0.9rem;
            }
            [data-testid="stMetricLabel"] { color: var(--muted); }

            [data-testid="stFileUploader"] {
                background: var(--surface);
                border: 1px solid var(--line);
                border-radius: 7px;
                padding: 0.35rem;
            }
            [data-testid="stFileUploaderDropzone"] {
                background: #fbfcfb;
                border: 1px dashed #aabdb7;
            }

            .stButton > button, .stDownloadButton > button {
                border-radius: 5px;
                font-weight: 700;
                min-height: 2.7rem;
            }
            .stButton > button[kind="primary"] {
                background: var(--coral);
                border-color: var(--coral);
            }
            .stButton > button[kind="primary"]:hover {
                background: #c9533d;
                border-color: #c9533d;
            }

            [data-testid="stExpander"] {
                background: var(--surface);
                border: 1px solid var(--line);
                border-radius: 7px;
            }
            div[data-testid="stSidebar"] {
                background: #edf3f0;
                border-right: 1px solid var(--line);
            }

            .app-hero::after {
                content: '';
                position: absolute;
                width: 210px;
                height: 210px;
                border: 1px solid rgba(255,255,255,0.16);
                border-radius: 50%;
                right: -70px;
                top: -95px;
            }

            .result-card {
                border: 1px solid var(--line);
                border-radius: 8px;
                padding: 15px 18px;
                margin-bottom: 10px;
                background: var(--surface);
                box-shadow: 0 2px 8px rgba(23,35,45,0.035);
            }
            .badge {
                display: inline-block;
                padding: 3px 12px;
                border-radius: 999px;
                font-size: 0.8rem;
                font-weight: 600;
            }
            .score-num {
                font: 700 1.75rem 'Space Grotesk', sans-serif;
                font-weight: 800;
            }
            .section-label {
                font-weight: 700;
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 0.03em;
                color: #6b7280;
                margin-top: 10px;
                margin-bottom: 4px;
            }
            .skill-pill {
                display: inline-block;
                padding: 2px 10px;
                margin: 2px 4px 2px 0;
                border-radius: 999px;
                font-size: 0.8rem;
            }
            .pill-good { background: #e8f7ee; color: #1a7f37; }
            .pill-bad { background: #fdecea; color: #c0362c; }

        </style>
        """,
        unsafe_allow_html=True,
    )


def skill_pills(items, kind: str) -> str:
    cls = "pill-good" if kind == "good" else "pill-bad"
    if not items:
        return "<span style='color:#9aa0a6; font-size:0.85rem;'>None listed</span>"
    return "".join(f"<span class='skill-pill {cls}'>{s}</span>" for s in items)


# --------------------------------------------------------------------------
# Streamlit UI
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Resume Screening and Matching Assistant",
    page_icon="🧑‍💼",
    layout="centered",
)
inject_css()

st.markdown(
    """
    <div class="app-hero">
        <h1>Resume Screening &amp; Matching Assistant</h1>
        <p>Turn a candidate pool into a focused shortlist with evidence-backed match scores.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- Sidebar: inputs live here so the main area stays focused on results ----
with st.sidebar:
    st.markdown('<div class="sidebar-title">Screening workspace</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subtitle">Add the role brief and candidate resumes to begin.</div>', unsafe_allow_html=True)
    st.markdown("#### 01 / Candidate pool")
    resume_files = st.file_uploader(
        "Resumes (PDF)", type=["pdf"], accept_multiple_files=True,
        help="Add one or more candidate resumes.",
    )
    jd_files = st.file_uploader(
        "Job description (TXT)", type=["txt"], accept_multiple_files=True,
        help="Add one or more job description files.",
    )

    st.markdown("#### 02 / Role brief")
    st.caption("Multiple TXT files are combined into one brief.")
    st.divider()
    min_score = st.slider("Minimum score to show", 0, 100, 0, 5)
    sort_desc = st.toggle("Sort highest score first", value=True)

    st.divider()
    run = st.button("🔍 Match Resumes", type="primary", use_container_width=True)

    with st.expander("ℹ️ How this works"):
        st.write(
            "Each resume is parsed, chunked, embedded, and matched against the "
            "job description using retrieval-augmented generation with Llama 3. "
            "The score reflects how well the resume's actual content covers the "
            "job requirements."
        )

    if not os.getenv("GROQ_API_KEY"):
        st.warning("GROQ_API_KEY is not set. Add it to your .env file before matching.")

if run:
    if not os.getenv("GROQ_API_KEY"):
        st.error("GROQ_API_KEY is missing. Add it to a .env file (see .env.example) and restart.")
    elif not resume_files or not jd_files:
        st.warning("Please upload at least one resume (PDF) and job description (TXT) in the sidebar.")
    else:
        jd_text = "\n\n".join(
            f"[Job Description: {jd_file.name}]\n"
            f"{jd_file.getvalue().decode('utf-8', errors='ignore')}"
            for jd_file in jd_files
        )
        matches = []
        progress = st.progress(0.0, text="Starting...")

        for i, resume_file in enumerate(resume_files, start=1):
            tmp_path = None
            try:
                progress.progress(
                    (i - 1) / len(resume_files),
                    text=f"Analyzing {resume_file.name} ({i}/{len(resume_files)})...",
                )
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(resume_file.getvalue())
                    tmp_path = tmp.name

                state: MatchState = {"resume_path": tmp_path, "jd_text": jd_text}
                state.update(load_resume(state))
                state.update(parse_job_description(state))
                state.update(index_resume(state))
                state.update(retrieve_context(state))
                state.update(analyze_match(state))
                final = state
                result = final["result"]
                score = max(0, min(100, int(result.get("match_score", 0))))
                matches.append(
                    {
                        "filename": resume_file.name,
                        "file_bytes": resume_file.getvalue(),
                        "score": score,
                        "result": result,
                        "context": final.get("context", ""),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                st.warning(f"Could not analyze {resume_file.name}: {exc}")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

        progress.progress(1.0, text="Done!")
        progress.empty()

        matches = [m for m in matches if m["score"] >= min_score]
        matches.sort(key=lambda m: m["score"], reverse=sort_desc)

        if not matches:
            st.info("No resumes matched your current filters. Try lowering the minimum score.")
        else:
            top = matches[0]
            avg_score = round(sum(m["score"] for m in matches) / len(matches))
            c1, c2, c3 = st.columns(3)
            c1.metric("Resumes analyzed", len(matches))
            c2.metric("Average score", f"{avg_score}%")
            c3.metric("Top candidate", f"{top['score']}%")

            qualifying_matches = [m for m in matches if m["score"] > 50]
            if qualifying_matches:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                    for rank, match in enumerate(qualifying_matches, start=1):
                        filename = os.path.basename(match["filename"])
                        archive_name = f"{rank:02d}_{match['score']}pct_{filename}"
                        archive.writestr(archive_name, match["file_bytes"])
                st.download_button(
                    f"⬇️ Download Resumes Above 50% ({len(qualifying_matches)})",
                    data=zip_buffer.getvalue(),
                    file_name="resumes_above_50_percent.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

            st.markdown(
                '<div class="result-heading"><h2>Ranked results</h2>'
                '<p>Compare candidates by match score and recommendation.</p></div>',
                unsafe_allow_html=True,
            )

            for rank, match in enumerate(matches, start=1):
                result = match["result"]
                rec = result.get("recommendation", "N/A")
                style = REC_STYLE.get(rec, {"color": "#374151", "bg": "#f3f4f6", "icon": "⚪"})
                color = score_color(match["score"])

                st.markdown(
                    f"""
                    <div class="result-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <div style="font-weight:700; font-size:1.05rem;">
                                    #{rank} — {match['filename']}
                                </div>
                                <span class="badge" style="background:{style['bg']}; color:{style['color']};">
                                    {style['icon']} {rec}
                                </span>
                            </div>
                            <div class="score-num" style="color:{color};">{match['score']}%</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                with st.expander("View details", expanded=(rank == 1)):
                    st.progress(match["score"] / 100)
                    st.write(result.get("summary", ""))

                    left, right = st.columns(2)
                    with left:
                        st.markdown('<div class="section-label">Matched skills</div>', unsafe_allow_html=True)
                        st.markdown(skill_pills(result.get("matched_skills", []), "good"), unsafe_allow_html=True)
                        st.markdown('<div class="section-label">Strengths</div>', unsafe_allow_html=True)
                        for s in result.get("strengths", []):
                            st.markdown(f"- {s}")
                    with right:
                        st.markdown('<div class="section-label">Missing skills</div>', unsafe_allow_html=True)
                        st.markdown(skill_pills(result.get("missing_skills", []), "bad"), unsafe_allow_html=True)
                        st.markdown('<div class="section-label">Concerns</div>', unsafe_allow_html=True)
                        for c in result.get("concerns", []):
                            st.markdown(f"- {c}")

                    with st.expander("Retrieved resume context (RAG)"):
                        st.text(match["context"])
else:
    st.markdown(
        """
        <div class="empty-state">
            <strong>Your shortlist will appear here.</strong><br>
            Upload resumes and one or more job descriptions in the sidebar,
            then run the match analysis.
        </div>
        """,
        unsafe_allow_html=True,
    )