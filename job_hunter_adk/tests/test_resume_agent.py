import pytest
from unittest.mock import patch
from schemas.resume_profile import ResumeProfile
from sub_agents.resume_agent.tools import _parse_resume_impl, _ats_score_impl

def test_parse_resume_returns_valid_profile():
    fake_resume = """
    John Doe
    Skills: Python, Machine Learning, Data Analysis
    Experience:
    Software Engineer at Tech Corp (2020-2023)
    - Developed awesome features.
    Education:
    B.S. in Computer Science, State University, 2019
    """
    
    # Mock the LLM output to return a perfectly formed JSON string matching ResumeProfile schema
    fake_llm_json = '''
    {
      "skills": ["Python", "Machine Learning", "Data Analysis"],
      "experience": [
        {
          "title": "Software Engineer",
          "company": "Tech Corp",
          "duration": "2020-2023",
          "description": "Developed awesome features."
        }
      ],
      "internships": [],
      "certifications": [],
      "education": [
        {
          "degree": "B.S. in Computer Science",
          "institution": "State University",
          "year": "2019"
        }
      ],
      "projects": []
    }
    '''
    
    # We patch the model's generate() to return our fake JSON so we test the parsing/validation logic
    class DummyResponse:
        text = fake_llm_json
        
    class DummyModel:
        def generate(self, prompt):
            return DummyResponse()

    with patch('sub_agents.resume_agent.tools.get_model', return_value=DummyModel()):
        profile = _parse_resume_impl(fake_resume)
        
        # Assert the returned object validates as ResumeProfile
        assert isinstance(profile, ResumeProfile)
        assert "Python" in profile.skills
        assert len(profile.experience) == 1
        assert profile.experience[0].company == "Tech Corp"

def test_ats_score():
    profile = ResumeProfile(
        skills=["Python", "Docker"],
        experience=[],
        internships=[],
        certifications=[],
        education=[],
        projects=[]
    )
    job_desc = "We need a Python developer who knows Docker and Kubernetes."
    result = _ats_score_impl(profile, job_desc)
    
    assert "score" in result
    assert "missing_keywords" in result
    assert "kubernetes" in result["missing_keywords"]
