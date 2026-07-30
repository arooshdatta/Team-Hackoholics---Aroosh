from db.connection import get_pool
import json

JSONB_FIELDS = ("skills", "mvp_features", "cut_features", "missing_pieces", "roadmap")

async def get_team(chat_id: int):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM teams WHERE chat_id = $1", chat_id
    )
    return dict(row) if row else None

async def create_team(chat_id: int, **fields):
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO teams (chat_id, team_name, deadline, headcount, skills)
           VALUES ($1, $2, $3, $4, $5) RETURNING *""",
        chat_id,
        fields.get("team_name"),
        fields.get("deadline"),
        fields.get("headcount"),
        json.dumps(fields.get("skills", {})),
    )
    return dict(row)

async def update_team(team_id: int, **fields):
    pool = await get_pool()
    set_clauses = []
    values = []
    for i, (key, val) in enumerate(fields.items(), start=1):
        set_clauses.append(f"{key} = ${i}")
        values.append(json.dumps(val) if key in JSONB_FIELDS else val)
    values.append(team_id)
    query = f"UPDATE teams SET {', '.join(set_clauses)} WHERE id = ${len(values)} RETURNING *"
    row = await pool.fetchrow(query, *values)
    return dict(row)

async def create_task(team_id: int, title: str, assigned_to: str, reasoning: str, target_hour: int):
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO tasks (team_id, title, assigned_to, reasoning, target_hour)
           VALUES ($1, $2, $3, $4, $5) RETURNING *""",
        team_id, title, assigned_to, reasoning, target_hour,
    )
    return dict(row)

async def create_checkin(task_id: int, team_id: int, author: str, message: str, is_blocked: bool):
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO checkins (task_id, team_id, author, message, is_blocked)
           VALUES ($1, $2, $3, $4, $5) RETURNING *""",
        task_id, team_id, author, message, is_blocked,
    )
    return dict(row)

async def get_checkins(team_id: int):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM checkins WHERE team_id = $1 ORDER BY created_at", team_id
    )
    return [dict(r) for r in rows]

async def get_tasks(team_id: int):
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM tasks WHERE team_id = $1 ORDER BY created_at", team_id
    )
    return [dict(r) for r in rows]

def _parse_json_fields(row_dict):
    for key in JSONB_FIELDS:
        if row_dict.get(key) is not None and isinstance(row_dict[key], str):
            row_dict[key] = json.loads(row_dict[key])
    return row_dict