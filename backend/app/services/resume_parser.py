import re
from typing import List, Dict, Set, Tuple
from pypdf import PdfReader
from io import BytesIO

# Standard technical taxonomy for skill matching
COMMON_SKILLS = {
    # Languages
    "python", "javascript", "typescript", "golang", "go", "java", "c++", "c#", "rust", "sql", "html", "css",
    # Frameworks & Libraries
    "fastapi", "django", "flask", "react", "next.js", "vue", "angular", "node.js", "express", 
    "pydantic", "sqlalchemy", "celery", "pandas", "numpy", "opencv", "pillow",
    # Databases & Storage
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch", "sqlite",
    # Cloud & DevOps
    "docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "git", "linux", "terraform",
    # Architecture & Tools
    "rest", "restful", "graphql", "microservices", "kafka", "rabbitmq", "distributed systems", "system design"
}

class ResumeParser:
    """Parses candidate profile/resumes and computes match telemetry against job specs."""

    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """Extracts text content from a raw PDF file buffer."""
        try:
            reader = PdfReader(BytesIO(pdf_bytes))
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n".join(text_parts)
        except Exception as e:
            return f"Error extracting text from PDF: {str(e)}"

    @staticmethod
    def extract_skills(text: str) -> List[str]:
        """Extracts technical skills and competencies from text using token matching."""
        normalized = text.lower()
        found_skills = set()
        
        # Tokenize words and punctuation
        words = set(re.findall(r"\b[a-z0-9\.\+#\-]+\b", normalized))
        
        for skill in COMMON_SKILLS:
            if skill in words or f" {skill} " in f" {normalized} ":
                found_skills.add(skill.title() if len(skill) > 3 else skill.upper())
                
        return sorted(list(found_skills))

    @classmethod
    def calculate_match(cls, candidate_text: str, job_description: str) -> Tuple[int, List[str], List[str]]:
        """
        Calculates a real skill overlap score (0-100), matching skills, and missing skills.
        Ensures ungrounded or mismatched profiles score 0% rather than an inflated baseline.
        """
        if not candidate_text:
            job_skills = set(s.lower() for s in cls.extract_skills(job_description))
            return 0, [], [s.title() if len(s) > 3 else s.upper() for s in sorted(list(job_skills))]

        candidate_skills = set(s.lower() for s in cls.extract_skills(candidate_text))
        job_skills = set(s.lower() for s in cls.extract_skills(job_description))

        if not job_skills:
            return 0, [], []

        matching = candidate_skills.intersection(job_skills)
        missing = job_skills.difference(candidate_skills)

        # Real mathematical skill overlap percentage
        match_ratio = len(matching) / len(job_skills) if job_skills else 0.0
        score = int(round(match_ratio * 100))
        score = min(100, max(0, score))

        formatted_matching = [s.title() if len(s) > 3 else s.upper() for s in sorted(list(matching))]
        formatted_missing = [s.title() if len(s) > 3 else s.upper() for s in sorted(list(missing))]

        return score, formatted_matching, formatted_missing

resume_parser = ResumeParser()

