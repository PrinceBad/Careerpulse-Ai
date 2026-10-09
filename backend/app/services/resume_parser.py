import re
from typing import List, Dict, Set, Tuple, Optional
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

    @staticmethod
    def detect_role(text: str) -> Optional[str]:
        """Heuristically detects primary role title from the first lines of resume text."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:10]:
            # Common role title matches
            m = re.search(
                r"\b((?:(?:Senior|Lead|Staff|Principal|Junior|Python|Backend|Frontend|Full[\s-]Stack|Software|Systems|Data|AI|ML|Machine Learning|Platform|DevOps|Cloud|Infrastructure)\s+)*(?:Engineer|Developer|Architect|Specialist))\b",
                line,
                re.IGNORECASE
            )
            if m:
                return m.group(1).strip()
        return None

    @staticmethod
    def detect_location(text: str) -> Optional[str]:
        """Detects candidate location from the header of resume text."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        header = " ".join(lines[:8]).lower()
        if "bengaluru" in header or "bangalore" in header:
            return "Bengaluru, India"
        if "delhi" in header or "noida" in header or "gurugram" in header or "gurgaon" in header:
            return "Delhi NCR, India"
        if "mumbai" in header:
            return "Mumbai, India"
        if "hyderabad" in header:
            return "Hyderabad, India"
        if "pune" in header:
            return "Pune, India"
        if "remote" in header:
            return "Remote, India"
        return None

    @classmethod
    def build_candidate_snippet(cls, text: str, max_chars: int = 500) -> str:
        """Extracts a high-impact technical skills and accomplishments snippet from resume text."""
        skills = cls.extract_skills(text)
        skills_str = ", ".join(skills[:12]) if skills else "Python, FastAPI, Microservices"
        
        # Look for quantifiable accomplishment lines (e.g. 10k req/sec, low-latency, 99.9%)
        metrics = []
        for line in text.splitlines():
            line_str = line.strip().lstrip("-*• ")
            if any(re.search(pat, line_str, re.IGNORECASE) for pat in [r"\d+k", r"\d+%", r"\d+ms", r"req/sec", r"requests", r"throughput", r"latency"]):
                if len(line_str) > 15 and len(line_str) < 180:
                    metrics.append(line_str)
                    if len(metrics) >= 2:
                        break
        
        if metrics:
            return f"{skills_str}. Key achievements: {' '.join(metrics)}"
        return skills_str

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

