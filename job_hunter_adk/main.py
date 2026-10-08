import sys
import os
from dotenv import load_dotenv
load_dotenv()

import logging
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from agent import root_agent

logger = logging.getLogger(__name__)

def main():
    print("Welcome to Job Hunter ADK! (Smoke test CLI)")
    print("Type 'exit' or 'quit' to stop.\n")
    
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        session_service=session_service,
        app_name="job_hunter_adk",
        auto_create_session=True,
    )
    
    user_id = "cli-user"
    session_id = "cli-session"

    initial_state = {
        "preferences": {
            "job_type": "full-time",
            "work_mode": "remote",
            "locations": ["New York"],
            "paid_only": True
        },
        "resume_raw": "Software Engineer with 5 years of Python experience."
    }
    
    session_service.create_session_sync(
        app_name="job_hunter_adk",
        user_id=user_id,
        session_id=session_id,
        state=initial_state,
    )
    
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            msg = types.Content(role="user", parts=[types.Part.from_text(text=user_input)])
            response_text = ""
            for event in runner.run(user_id=user_id, session_id=session_id, new_message=msg):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text
            print(f"Agent: {response_text or 'Turn completed.'}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
