import sys
import os
from dotenv import load_dotenv
load_dotenv()

try:
    from google.adk.runner import Runner
    from google.adk.services import SessionService
except ImportError:
    class Runner:
        def __init__(self, agent, session_service):
            self.agent = agent
            self.session_service = session_service
            
        def run(self, message, state=None):
            print(f"Runner received: {message}")
            return {"response": "Mock runner response", "state": state}
            
    class SessionService:
        pass

from agent import root_agent

def main():
    print("Welcome to Job Hunter ADK! (Smoke test CLI)")
    print("Type 'exit' or 'quit' to stop.\n")
    
    session_service = SessionService()
    runner = Runner(agent=root_agent, session_service=session_service)
    
    # Pre-populate state for smoke test
    initial_state = {
        "preferences": {
            "job_type": "full-time",
            "work_mode": "remote",
            "locations": ["New York"],
            "paid_only": True
        },
        "resume_raw": "Software Engineer with 5 years of Python experience."
    }
    
    # In a real ADK Runner, state might be attached to the session service or passed in run().
    # Here we mock it by attaching it to the runner or just assuming the agent fetches it.
    
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            # Simulated run with initial state
            response = runner.run(user_input, state=initial_state)
            print(f"Agent: {response}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
