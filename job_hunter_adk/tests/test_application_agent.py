import pytest
from sub_agents.application_agent.tools import _send_email_impl

def test_send_email_refuses_when_not_confirmed():
    draft = {
        "to": "hr@company.com",
        "subject": "Application",
        "body": "Cover letter",
        "status": "pending_user_approval"
    }
    
    result_false = _send_email_impl(draft, user_confirmed=False)
    assert result_false["status"] == "not_sent"
    assert "awaiting confirmation" in result_false["reason"]

    result_true = _send_email_impl(draft, user_confirmed=True)
    assert result_true["status"] == "sent"
    assert "user confirmed" in result_true["reason"]
