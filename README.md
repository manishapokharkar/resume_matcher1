# Resume Screening and Matching Assistant

Streamlit app: upload resumes (PDF) and a job description (TXT), then click
**Match Resumes**. Successfully matched resumes can be downloaded together as a
ZIP file.

Pipeline: PyPDFLoader extracts resume text; job description URLs are parsed and
scraped with BeautifulSoup and Requests; resume sections are chunked and embedded
with MiniLM in Chroma; relevant sections are retrieved for each job requirement;
and Llama via Groq scores the match.

## Setup (Windows / Python 3.10 or 3.11 recommended)

```powershell
cd resume_matcher
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Add your Groq API key to `.env`, then start the app:

```powershell
streamlit run app.py --server.port 8502
```

Get a free Groq API key at <https://console.groq.com/keys> and open
<http://localhost:8502>.

## Deploy to Streamlit Community Cloud

1. Push this project to a GitHub repository. Do not commit `.env`,
   `.streamlit/secrets.toml`, API keys, or resume files containing personal
   information.
2. Sign in at <https://share.streamlit.io/> and choose **Create app**.
3. Select the repository and branch. Set the main file path to `app.py` for the
   resume-upload matcher, or `app_outlook.py` for the Outlook integration app.
4. In the app's **Settings > Secrets**, add:

   ```toml
   GROQ_API_KEY = "your-groq-api-key"
   GROQ_MODEL = "openai/gpt-oss-120b"
   ```

5. Deploy. Streamlit Cloud installs the packages listed in `requirements.txt`.
   The first request may take longer while the MiniLM embedding model downloads.

For local development with Streamlit secrets, copy
`.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and replace the
placeholder key. The real secrets file is ignored by Git. The app also supports
the `.env` setup described above.

## Notes

- The first run downloads the MiniLM embedding model.
- Change the Groq model with `GROQ_MODEL` in `.env` or Streamlit secrets (the
  default is `openai/gpt-oss-120b`).
- Scanned (image-only) PDFs have no extractable text and will show an error.
