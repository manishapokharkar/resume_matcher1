import streamlit as st

from match_candidates import match_candidates
from outlook_sync import sync_outlook


st.set_page_config(
    page_title="Talent Desk | Resume Matcher",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ROLE_EXAMPLES = {
    "Frontend Developer": """Frontend Developer\n\nBuild accessible, responsive web experiences with React and TypeScript.\n\nRequired skills:\nReact, JavaScript, TypeScript, HTML, CSS, Git\n\nNice to have:\nNext.js, Tailwind CSS\n\nExperience: 2+ years""",
    "Data Analyst": """Data Analyst\n\nTurn business data into clear insights and actionable recommendations.\n\nRequired skills:\nSQL, Python, Excel, Power BI\n\nNice to have:\nSnowflake, dbt\n\nExperience: 3+ years""",
    "Python Backend Engineer": """Python Backend Engineer\n\nDesign reliable APIs and services for a growing product.\n\nRequired skills:\nPython, FastAPI, PostgreSQL, Docker, Git\n\nNice to have:\nAWS, MongoDB\n\nExperience: 3+ years""",
}

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
        :root {
            --ink: #172a30;
            --muted: #68777a;
            --line: #d9e2dd;
            --paper: #f3f6f2;
            --surface: #ffffff;
            --teal: #167b72;
            --coral: #e4775c;
        }
        .stApp, [data-testid="stMain"] { background: var(--paper); color: var(--ink); }
        body, p, label, input, button { font-family: 'DM Sans', sans-serif; }
        h1, h2, h3, [data-testid="stMetricValue"] { font-family: 'Space Grotesk', sans-serif; color: var(--ink); }
        .main > div { padding-top: 1.2rem; }
        #MainMenu, footer { visibility: hidden; }
        .desk-hero {
            background: #193d40;
            color: #f9f6ee;
            padding: 1.7rem 2rem;
            border-radius: 8px;
            margin-bottom: 1.4rem;
            position: relative;
            overflow: hidden;
        }
        .desk-hero:after {
            content: '';
            position: absolute;
            width: 210px;
            height: 210px;
            border: 1px solid rgba(244, 229, 193, .32);
            border-radius: 50%;
            right: -60px;
            top: -115px;
        }
        .desk-kicker { color: #f3b18f; font-size: .74rem; font-weight: 700; text-transform: uppercase; letter-spacing: .12em; }
        .desk-hero h1 { color: #fffdf6; font-size: 2.25rem; line-height: 1.08; margin: .45rem 0 .5rem; }
        .desk-hero p { color: #d9e9df; max-width: 620px; margin: 0; }
        .section-kicker { color: var(--teal); font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; }
        .sync-panel {
            background: #e7eeea;
            border-left: 4px solid var(--coral);
            border-radius: 5px;
            padding: 1rem 1.1rem;
            margin: .2rem 0 .8rem;
        }
        .sync-panel strong { color: var(--ink); font-family: 'Space Grotesk', sans-serif; font-size: 1.04rem; }
        .sync-panel p { color: var(--muted); font-size: .88rem; margin: .35rem 0 0; }
        [data-testid="stMetric"] { background: var(--surface); border: 1px solid var(--line); border-top: 3px solid var(--teal); border-radius: 6px; padding: .75rem .9rem; }
        [data-testid="stMetricLabel"] { color: var(--muted); }
        [data-testid="stTextArea"] textarea { background: var(--surface); border-color: #c7d4cd; border-radius: 6px; }
        .stButton > button, .stDownloadButton > button { border-radius: 5px; min-height: 2.65rem; font-weight: 700; }
        .stButton > button[kind="primary"] { background: var(--coral); border-color: var(--coral); color: #18282c; }
        .stButton > button[kind="primary"]:hover { background: #ef8d70; border-color: #ef8d70; }
        [data-testid="stExpander"] { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; }
        @media (max-width: 700px) {
            .desk-hero { padding: 1.3rem; }
            .desk-hero h1 { font-size: 1.8rem; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <header class="desk-hero">
        <div class="desk-kicker">Talent Desk / Candidate intelligence</div>
        <h1>Find the signal in every resume.</h1>
        <p>Bring in applications from Outlook, shape a role brief, and build a shortlist grounded in candidate skills.</p>
    </header>
    """,
    unsafe_allow_html=True,
)

if "sync_report" not in st.session_state:
    st.session_state.sync_report = None
if "sync_error" not in st.session_state:
    st.session_state.sync_error = None
if "match_results" not in st.session_state:
    st.session_state.match_results = None

brief_column, sync_column = st.columns([1.55, 0.8], gap="large")

with brief_column:
    st.markdown('<div class="section-kicker">01 / Define the role</div>', unsafe_allow_html=True)
    st.subheader("Start with a role brief")
    template = st.selectbox(
        "Quick-start with a role",
        ["Write from scratch", *ROLE_EXAMPLES.keys()],
        label_visibility="collapsed",
    )
    if st.button("Load example brief", help="Replace the current text with the selected role example"):
        st.session_state.job_description = ROLE_EXAMPLES.get(template, "")
    job_description = st.text_area(
        "Job description",
        key="job_description",
        height=255,
        placeholder="Paste the role, required skills, and experience level...",
        label_visibility="collapsed",
    )
    st.caption("Skills in the brief are compared with the candidates already in your database.")
    match_clicked = st.button("Build shortlist", type="primary", use_container_width=True)

with sync_column:
    st.markdown('<div class="section-kicker">02 / Bring in candidates</div>', unsafe_allow_html=True)
    st.subheader("Outlook inbox")
    st.markdown(
        '<div class="sync-panel"><strong>Application intake</strong><p>Scan your inbox for job-related messages and save new resume attachments.</p></div>',
        unsafe_allow_html=True,
    )
    sync_clicked = st.button("🔄 Sync Outlook", use_container_width=True)
    if st.session_state.sync_report:
        report = st.session_state.sync_report
        st.success(f"Last sync complete · {report['saved']} candidates added")
        sync_metrics = st.columns(3)
        sync_metrics[0].metric("New files", report["downloaded"])
        sync_metrics[1].metric("Skipped", report["skipped"])
        sync_metrics[2].metric("Saved", report["saved"])
    elif st.session_state.sync_error:
        st.error(f"Outlook sync failed: {st.session_state.sync_error}")

if sync_clicked:
    with st.spinner("Checking Outlook for new applications..."):
        try:
            st.session_state.sync_report = sync_outlook()
            st.session_state.sync_error = None
        except Exception as error:
            st.session_state.sync_report = None
            st.session_state.sync_error = str(error)
    st.rerun()

if match_clicked:
    if not job_description.strip():
        st.warning("Add a job description before building the shortlist.")
    else:
        with st.spinner("Comparing the role brief with saved candidates..."):
            try:
                st.session_state.match_results = match_candidates(job_description)
            except Exception as error:
                st.session_state.match_results = None
                st.error(f"Could not build the shortlist: {error}")

if st.session_state.match_results is not None:
    results = st.session_state.match_results
    st.markdown("---")
    st.markdown('<div class="section-kicker">03 / Review the shortlist</div>', unsafe_allow_html=True)
    st.subheader("Candidate matches")

    if not results:
        st.info("No candidates are saved yet. Sync Outlook to bring in resume attachments.")
    else:
        filter_column, search_column = st.columns([0.75, 1.25])
        with filter_column:
            minimum_score = st.slider("Minimum match score", 0, 100, 0, 5)
        with search_column:
            search_text = st.text_input("Find a candidate", placeholder="Search name, email, or skill")

        search_term = search_text.strip().lower()
        visible_results = [
            candidate for candidate in results
            if candidate["score"] >= minimum_score
            and search_term in " ".join(str(candidate.get(field, "")) for field in ("name", "email", "skills")).lower()
        ]
        if not visible_results:
            st.info("No candidates meet those filters. Lower the score threshold or adjust your search.")
        else:
            average_score = round(sum(candidate["score"] for candidate in visible_results) / len(visible_results))
            best_candidate = visible_results[0]
            summary_columns = st.columns(3)
            summary_columns[0].metric("In shortlist", len(visible_results), f"of {len(results)} candidates")
            summary_columns[1].metric("Average fit", f"{average_score:.0f}%")
            summary_columns[2].metric("Top match", f"{best_candidate['score']:.0f}%", best_candidate["name"] or "Candidate")

            for rank, candidate in enumerate(visible_results, start=1):
                name = candidate.get("name") or "Unnamed candidate"
                score = candidate["score"]
                with st.expander(f"#{rank}  {name}  ·  {score:.0f}% match", expanded=(rank == 1)):
                    st.progress(max(0, min(100, int(score))) / 100)
                    st.write(candidate.get("email") or "No email listed")
                    st.write(f"**Experience:** {candidate.get('experience') or 'Not listed'}")
                    matched_column, missing_column = st.columns(2)
                    with matched_column:
                        st.markdown("**Matching skills**")
                        st.write(candidate.get("matched_skills") or "No matching skills identified")
                    with missing_column:
                        st.markdown("**Skills to verify**")
                        st.write(candidate.get("missing_skills") or "No listed gaps")
