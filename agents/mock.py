# Temporary hardcoded mocks matching Section 4 contract signatures

def run_critic(team_id: int) -> dict:
    return {
        "mvp_features": [{"feature": "Telegram Webhook", "why_mvp": "Core interface"}],
        "cut_features": [{"feature": "Custom UI", "why_cut": "Out of scope"}],
        "missing_pieces": [{"gap": "Auth", "why_it_matters": "Security"}],
        "risk_note": "Ensure webhook responsiveness."
    }

def run_planner(team_id: int) -> dict:
    return {
        "tasks": [{"title": "Setup Webhook", "assigned_to": "P2", "reasoning": "Gateway", "target_hour": 2}],
        "roadmap": [{"milestone": "Bot MVP", "target_hour": 2}]
    }

def run_pitch(team_id: int) -> dict:
    return {
        "problem": "Async hackathon sync is hard.",
        "solution": "Huddle Telegram Bot",
        "what_we_built": ["Webhook", "Critic agent"],
        "not_demoed": ["Full DB sync"],
        "demo_flow": ["Send /critique", "Receive breakdown"]
    }

def run_blocker_check(team_id: int) -> dict:
    return {
        "blocked_tasks": [],
        "should_escalate": False,
        "escalation_message": ""
    }

def get_team_mock(team_id: int) -> dict:
    return {"id": team_id, "name": "Hackaholics Team"}