"""
agents/critic.py — ScopeAndGapCritic agent (P3)

Exposes:
    run_critic(team_id: int) -> dict

Reads team context from Postgres (via db/queries.py — never imports another
teammate's module directly), runs a CrewAI agent that critiques scope and
flags missing pieces, writes the result back into the `teams` table, and
returns the same dict to the caller (P2's webhook).

Contract (frozen in Huddle kickoff doc, section 4) — do not change without
telling the group:
    {
        "mvp_features": [{"feature": str, "why_mvp": str}],
        "cut_features": [{"feature": str, "why_cut": str}],
        "missing_pieces": [{"gap": str, "why_it_matters": str}],
        "risk_note": str
    }
"""

import asyncio
import json
import os

from crewai import Agent, Task, Crew, Process
from crewai.llm import LLM

from db import queries


# --------------------------------------------------------------------------
# Async bridge — db/queries.py is asyncpg-based (async), but the contract in
# section 4 requires run_critic() to be a plain sync function so P2 can call
# it without awaiting. This bridges the two.
# --------------------------------------------------------------------------
def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        # We're already inside an event loop (e.g. called from an async
        # FastAPI route without being awaited properly). Use nest_asyncio
        # as a safety net rather than crashing.
        import nest_asyncio

        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    return asyncio.run(coro)


def _get_llm() -> LLM:
    # CrewAI's LLM class routes through LiteLLM, which supports Gemini
    # natively via the "gemini/<model>" prefix + GEMINI_API_KEY env var.
    # Swap the model string below if the team wants a different Gemini
    # tier (e.g. "gemini/gemini-2.5-pro" for higher quality, slower/pricier).
    return LLM(
        model=os.environ.get("GEMINI_MODEL", "gemini/gemini-2.0-flash"),
        api_key=os.environ["GEMINI_API_KEY"],
        temperature=0.3,
    )


def _fetch_team_context(team_id: int) -> dict:
    """
    NOTE FOR THE GROUP: section 4 only specifies `get_team(chat_id)`, keyed
    by chat_id — not team_id. P2 calls run_critic(team_id), so this module
    needs the team row by team_id. Until P1 adds a `get_team_by_id(team_id)`
    helper to db/queries.py, this falls back to a raw query so P3 isn't
    blocked. Raise this at the hour-2 sync.
    """
    if hasattr(queries, "get_team_by_id"):
        team = _run_async(queries.get_team_by_id(team_id))
    else:
        team = _run_async(_fallback_get_team_by_id(team_id))

    tasks = _run_async(queries.get_tasks(team_id))
    checkins = _run_async(queries.get_checkins(team_id))
    return {"team": team or {}, "tasks": tasks or [], "checkins": checkins or []}


async def _fallback_get_team_by_id(team_id: int) -> dict | None:
    """Temporary shim until db/queries.py exposes get_team_by_id(team_id)."""
    pool = getattr(queries, "pool", None)
    if pool is None:
        return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM teams WHERE id = $1", team_id)
        return dict(row) if row else None


def _build_agent() -> Agent:
    return Agent(
        role="Scope and Gap Critic",
        goal=(
            "Critique a hackathon team's planned scope honestly and surface "
            "missing pieces they haven't thought of yet."
        ),
        backstory=(
            "You've mentored and judged dozens of hackathon teams. You've seen "
            "demos fail because of an integration nobody built, an auth flow "
            "nobody planned, or a feature that sounded easy but wasn't. You're "
            "blunt but constructive — your job is to save the team from a bad "
            "demo, not to be nice."
        ),
        llm=_get_llm(),
        verbose=False,
        allow_delegation=False,
    )


def _build_task(agent: Agent, context: dict) -> Task:
    team = context["team"]
    tasks = context["tasks"]
    checkins = context["checkins"]

    prompt = f"""
Team: {team.get("team_name", "Unnamed team")}
Deadline: {team.get("deadline", "unknown")}
Headcount: {team.get("headcount", "unknown")}
Skills on team: {json.dumps(team.get("skills") or [])}
Features mentioned so far: {json.dumps(team.get("mvp_features") or [])}
Tasks logged: {json.dumps(tasks[:20], default=str)}
Recent check-ins: {json.dumps(checkins[-20:], default=str)}

Critique this team's scope for a time-boxed hackathon. Respond with ONLY a
JSON object — no markdown fences, no preamble, no commentary — matching
exactly this shape:

{{
  "mvp_features": [{{"feature": "string", "why_mvp": "string"}}],
  "cut_features": [{{"feature": "string", "why_cut": "string"}}],
  "missing_pieces": [{{"gap": "string", "why_it_matters": "string"}}],
  "risk_note": "string"
}}

Rules:
- mvp_features: only what's realistically demoable given headcount and deadline.
- cut_features: anything currently in scope that should be cut, with a reason.
- missing_pieces: things the team hasn't mentioned but will need (auth, error
  states, seed data, deployment, etc.) — specific to this project, not generic.
- risk_note: one or two sentences on the single biggest risk to a working demo.
- Output must be valid JSON and nothing else.
"""

    return Task(
        description=prompt,
        expected_output="A single JSON object matching the schema above, nothing else.",
        agent=agent,
    )


def _parse_llm_json(raw: str) -> dict:
    """LLM output sometimes wraps JSON in code fences — strip defensively."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


def run_critic(team_id: int) -> dict:
    context = _fetch_team_context(team_id)
    agent = _build_agent()
    task = _build_task(agent, context)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)

    raw_result = crew.kickoff()

    try:
        result = _parse_llm_json(str(raw_result))
    except (json.JSONDecodeError, ValueError):
        # Never let a malformed LLM response take down the webhook.
        result = {
            "mvp_features": [],
            "cut_features": [],
            "missing_pieces": [],
            "risk_note": "Critic agent returned unparseable output; check logs.",
        }

    for key in ("mvp_features", "cut_features", "missing_pieces"):
        result.setdefault(key, [])
    result.setdefault("risk_note", "")

    _run_async(
        queries.update_team(
            team_id,
            mvp_features=json.dumps(result["mvp_features"]),
            cut_features=json.dumps(result["cut_features"]),
            missing_pieces=json.dumps(result["missing_pieces"]),
        )
    )

    return result


if __name__ == "__main__":
    # Quick manual smoke test: python -m agents.critic <team_id>
    import sys

    tid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(json.dumps(run_critic(tid), indent=2))