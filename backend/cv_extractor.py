import io
import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """
    Extracts plain text from uploaded CV files (PDF, TXT, MD, DOCX).
    """
    ext = os.path.splitext(filename.lower())[1]
    
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages_text.append(text.strip())
            extracted = "\n\n".join(pages_text)
            if extracted.strip():
                return extracted.strip()
        except Exception as e:
            logger.warning(f"pypdf extraction failed for {filename}: {e}")
            
    # Plain text / Markdown fallback
    try:
        return file_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        try:
            return file_bytes.decode("latin-1").strip()
        except Exception as e:
            logger.error(f"Failed to decode text file: {e}")
            return ""

def parse_cv_with_gemini(cv_text: str, genai_client: Any = None) -> Dict[str, Any]:
    """
    Uses Gemini to extract structured project details, tech stack, and probing angles from CV text.
    """
    if not cv_text:
        return {
            "candidate_name": "Candidate",
            "summary": "Software Engineering Candidate",
            "skills": [],
            "projects": [],
            "experience": []
        }

    if genai_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            try:
                from dotenv import load_dotenv
                load_dotenv()
                api_key = os.getenv("GEMINI_API_KEY")
            except Exception:
                pass
        if api_key:
            try:
                from google import genai
                genai_client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.warning(f"Could not init genai client: {e}")

    if not genai_client:
        return {
            "candidate_name": "Candidate",
            "summary": "Software Engineering Candidate",
            "skills": ["Python", "FastAPI", "React"],
            "projects": [
                {
                    "name": "Flagship Project",
                    "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
                    "summary": "Core backend service project.",
                    "probing_angles": [
                        "Walk me through the end-to-end architecture.",
                        "Why did you choose this particular tech stack?",
                        "What was the most challenging scaling bottleneck you encountered?"
                    ]
                }
            ],
            "experience": []
        }

    prompt = f"""You are an elite technical recruiter and Senior Staff Engineer at a top tech company (Google/Meta).
Analyze the following candidate's CV/Resume text and extract structured information for a rigorous 25-30 minute technical grilling interview.

CV TEXT:
\"\"\"
{cv_text[:12000]}
\"\"\"

Return a valid JSON object matching this exact schema:
{{
  "candidate_name": "Candidate full name or Candidate",
  "summary": "2-3 sentence technical profile summary",
  "skills": ["Skill1", "Skill2", "Skill3"],
  "projects": [
    {{
      "name": "Project Name",
      "tech_stack": ["Tech1", "Tech2"],
      "summary": "What the project does and candidate's specific impact",
      "architecture_highlights": "Key architectural components, databases, queues, protocols used",
      "probing_angles": [
        "Probing question on tech stack selection trade-off",
        "Probing question on scaling, concurrency, or data consistency",
        "Probing question on failure handling, security, or edge cases"
      ]
    }}
  ],
  "experience": [
    {{
      "company": "Company Name",
      "role": "Role Title",
      "duration": "Duration or Years",
      "key_contributions": "Summary of key systems built"
    }}
  ]
}}

Provide ONLY raw JSON with no Markdown backticks or commentary."""

    models_to_try = ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"]
    for m in models_to_try:
        try:
            response = genai_client.models.generate_content(
                model=m,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.2
                }
            )
            data = json.loads(response.text)
            return data
        except Exception as e:
            logger.warning(f"Failed to parse CV with model {m}: {e}")

    return {
            "candidate_name": "Candidate",
            "summary": cv_text[:200],
            "skills": [],
            "projects": [
                {
                    "name": "Primary Project",
                    "tech_stack": ["General Software"],
                    "summary": cv_text[:300],
                    "probing_angles": [
                        "Can you walk me through the system architecture?",
                        "What trade-offs did you make in your design?"
                    ]
                }
            ],
            "experience": []
        }
