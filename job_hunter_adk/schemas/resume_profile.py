from pydantic import BaseModel, ConfigDict

class Experience(BaseModel):
    """
    A single work or internship experience.
    Extracted by the resume_agent from the user's raw resume.
    """
    model_config = ConfigDict(extra="forbid")
    
    title: str
    company: str
    duration: str
    description: str

class Education(BaseModel):
    """
    Educational background entry.
    Extracted by the resume_agent from the user's raw resume.
    """
    model_config = ConfigDict(extra="forbid")
    
    degree: str
    institution: str
    year: str

class ResumeProfile(BaseModel):
    """
    The structured representation of the candidate's profile.
    Written by the resume_agent after parsing the user's raw resume PDF/text.
    """
    model_config = ConfigDict(extra="forbid")
    
    skills: list[str]
    experience: list[Experience]
    internships: list[Experience]
    certifications: list[str]
    education: list[Education]
    projects: list[dict[str, str]]
