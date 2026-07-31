CREATE TABLE IF NOT EXISTS teams (
    id             SERIAL PRIMARY KEY,
    chat_id        BIGINT UNIQUE NOT NULL,
    team_name      TEXT,
    deadline       TIMESTAMP,
    headcount      INT,
    skills         JSONB,
    mvp_features   JSONB,
    cut_features   JSONB,
    missing_pieces JSONB,
    roadmap        JSONB,
    created_at     TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_teams_chat_id ON teams(chat_id);

CREATE TABLE IF NOT EXISTS tasks (
    id            SERIAL PRIMARY KEY,
    team_id       INT REFERENCES teams(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    reasoning     TEXT,
    assigned_to   TEXT,
    target_hour   INT,
    status        TEXT DEFAULT 'todo',
    created_at    TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tasks_team_id ON tasks(team_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status  ON tasks(status);

CREATE TABLE IF NOT EXISTS checkins (
    id            SERIAL PRIMARY KEY,
    task_id       INT REFERENCES tasks(id) ON DELETE CASCADE,
    team_id       INT REFERENCES teams(id) ON DELETE CASCADE,
    author        TEXT,
    message       TEXT,
    is_blocked    BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_checkins_team_id ON checkins(team_id);
CREATE INDEX IF NOT EXISTS idx_checkins_task_id ON checkins(task_id);

CREATE TABLE IF NOT EXISTS raw_messages (
    id            SERIAL PRIMARY KEY,
    team_id       INT REFERENCES teams(id) ON DELETE CASCADE,
    author        TEXT,
    message       TEXT,
    created_at    TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_raw_messages_team_id ON raw_messages(team_id);