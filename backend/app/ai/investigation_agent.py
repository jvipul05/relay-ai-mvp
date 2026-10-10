"""Adapter around the existing Gemini implementation in backend/ai_agent.py."""

def investigate_with_gemini(project: dict, investigation: dict):
    try:
        from ai_agent import investigate_with_gemini as existing_agent
    except ImportError as exc:
        raise RuntimeError(
            "Gemini agent module was not found. Keep your existing backend/ai_agent.py file in place."
        ) from exc
    return existing_agent(project, investigation)
