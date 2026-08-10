import os
from pathlib import Path

base_dir = Path(r"c:\Users\soumy\OneDrive\Desktop\Resume_Agent\job_hunter_adk")

files = [
    "README.md",
    "main.py",
    "agent.py",
    "sub_agents/__init__.py",
    "sub_agents/resume_agent/__init__.py",
    "sub_agents/resume_agent/agent.py",
    "sub_agents/resume_agent/prompt.py",
    "sub_agents/resume_agent/tools.py",
    "sub_agents/job_discovery_agent/__init__.py",
    "sub_agents/job_discovery_agent/agent.py",
    "sub_agents/job_discovery_agent/prompt.py",
    "sub_agents/job_discovery_agent/tools.py",
    "sub_agents/company_intel_agent/__init__.py",
    "sub_agents/company_intel_agent/agent.py",
    "sub_agents/company_intel_agent/prompt.py",
    "sub_agents/company_intel_agent/tools.py",
    "sub_agents/interview_agent/__init__.py",
    "sub_agents/interview_agent/agent.py",
    "sub_agents/interview_agent/prompt.py",
    "sub_agents/interview_agent/tools.py",
    "sub_agents/application_agent/__init__.py",
    "sub_agents/application_agent/agent.py",
    "sub_agents/application_agent/prompt.py",
    "sub_agents/application_agent/tools.py",
    "tools/__init__.py",
    "tools/match_rank_tool.py",
    "schemas/__init__.py",
    "schemas/preferences.py",
    "schemas/resume_profile.py",
    "schemas/job_listing.py",
    "schemas/company_intel.py",
    "services/__init__.py",
    "services/scrapers/__init__.py",
    "services/scrapers/linkedin_scraper.py",
    "services/scrapers/naukri_scraper.py",
    "services/scrapers/internshala_scraper.py",
    "services/scrapers/indeed_scraper.py",
    "services/scrapers/glassdoor_scraper.py",
    "services/ats_scorer.py",
    "services/embeddings.py",
    "services/db.py",
    "ui/__init__.py",
    "ui/app.py",
    "tests/__init__.py",
    "tests/test_smoke.py"
]

for f in files:
    p = base_dir / f
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch(exist_ok=True)
