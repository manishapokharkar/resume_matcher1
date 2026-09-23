# Resume Screening and Matching Assistant

Streamlit app: upload resumes (PDF) + a job description (TXT) and click **Match Resumes**.
The ranked, successfully matched resumes can be downloaded together as a ZIP file.

Pipeline: PyPDFLoader -> parse JD (BeautifulSoup + Requests scrape any URLs in the JD)
-> chunk + embed resume (MiniLM sentence-transformer) into Chroma -> retrieve relevant
sections per JD requirement (RAG) -> Llama 3 via Groq scores the match.

## Setup (Windows / Python 3.10 or 3.11 recommended)

```
cd resume_matcher
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      (then paste your Groq key into .env)
streamlit run app.py --server.port 8502
```

Get a free Groq API key at https://console.groq.com/keys

Open http://localhost:8502

## Notes
- First run downloads the MiniLM embedding model.
- Change the Groq model with `GROQ_MODEL` in `.env` (the default is `openai/gpt-oss-120b`).
- Scanned (image-only) PDFs have no extractable text and will show an error.
