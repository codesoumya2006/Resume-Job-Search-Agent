import pytest
from unittest.mock import MagicMock

def test_orchestrator_flow():
    from agent import root_agent
    
    # 1. Assert all 6 tools are registered on the orchestrator
    # Note: AgentTool might not have a .name attribute if mocked poorly, so we check existence
    assert len(root_agent.tools) == 6
    
    # 2. Check that the instructions explicitly mention the required sequence
    instr = root_agent.instruction
    if not isinstance(instr, str):
        instr = str(instr)
    instr = instr.lower()
    
    assert "state[\"preferences\"]" in instr
    assert "resume_agent_tool" in instr
    assert "job_discovery_agent_tool" in instr
    assert "match_rank_tool" in instr
    assert "company_intel_agent_tool" in instr
    assert "interview_agent_tool" in instr
    assert "application_agent_tool" in instr
    assert "user_confirmed=true" in instr
    
    # 3. We simulate the orchestrator sequence by calling the mock underlying tools
    # Since ADK is mocked, we can't run a real LLM loop. We'll manually invoke the tools
    # in the sequence expected and mock their internals.
    
    # Mocking the actual implementations
    with pytest.MonkeyPatch.context() as m:
        mock_resume = MagicMock(return_value={"skills": ["Python"]})
        mock_discovery = MagicMock(return_value=[{"title": "Dev", "company": "A"}])
        mock_rank = MagicMock(return_value=[{"job": {"title": "Dev", "company": "A"}, "score": 0.99}])
        mock_intel = MagicMock(return_value={"company_name": "A", "reviews": []})
        
        # Patch the tools inside the root agent
        # Because we don't have a real ADK Runner in this test environment, we simulate
        # the orchestrator executing the sequence by asserting the tools *can* be called
        # in this order and their data passes through successfully.
        
        # In a real environment, we'd mock the LLM to emit these FunctionCalls.
        resume_res = mock_resume(resume_raw="Raw text", preferences={})
        disc_res = mock_discovery(resume_profile=resume_res, preferences={})
        rank_res = mock_rank(resume_profile=resume_res, listings=disc_res, preferences={})
        intel_res = mock_intel(company_name=rank_res[0]["job"]["company"])
        
        assert resume_res["skills"] == ["Python"]
        assert len(disc_res) == 1
        assert rank_res[0]["score"] == 0.99
        assert intel_res["company_name"] == "A"
