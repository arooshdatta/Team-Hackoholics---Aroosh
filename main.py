import os
import logging
from fastapi import FastAPI, Request, BackgroundTasks
from contextlib import asynccontextmanager

from db.queries import get_team, create_team, create_raw_message
from agents.critic import run_critic
from agents.planner import run_planner
from agents.pitch import run_pitch
from agents.blocker import run_blocker_check
from telegram_client import send_telegram_message, bot

from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    # Process telegram update here...
    return {"status": "ok"}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("P2-Webhook")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Register the Telegram Webhook automatically
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url and bot:
        full_url = f"{webhook_url}/webhook"
        await bot.set_webhook(url=full_url)
        logger.info(f"Telegram webhook set to: {full_url}")
    yield


app = FastAPI(title="Huddle Webhook", lifespan=lifespan)


@app.get("/")
def read_root():
    return {"status": "ok", "role": "P2 Telegram/Webhook Router"}


@app.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receives incoming updates from Telegram and routes commands/messages to DB and agents."""
    data = await request.json()

    if "message" not in data:
        return {"status": "ignored"}

    message = data["message"]
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    author = message.get("from", {}).get("username", "Unknown")

    if not chat_id or not text:
        return {"status": "ignored"}

    # Fetch team from DB or auto-create if it doesn't exist
    team = await get_team(chat_id)
    if not team:
        team = await create_team(chat_id)

    team_id = team["id"]

    # Log every raw incoming message into PostgreSQL
    await create_raw_message(team_id=team_id, author=author, message=text)

    # Command Routing
    if text.startswith("/start"):

        async def send_welcome():
            welcome_msg = (
                "👋 **Welcome to Huddle Bot**!\n\n"
                "Available commands:\n"
                "• `/critique` - Scope critique & gap analysis\n"
                "• `/plan` - Milestone roadmap & task split\n"
                "• `/pitch` - Pitch outline from check-ins\n"
                "• `/blocker` - Check for active blockers"
            )
            await send_telegram_message(chat_id, welcome_msg)

        background_tasks.add_task(send_welcome)

    elif text.startswith("/critique"):

        async def process_critique():
            res = await run_critic(team_id=team_id)
            msg = "🔍 **Scope Critique**:\n\n**MVP Features:**\n"
            for item in res.get("mvp_features", []):
                msg += f"- {item['feature']}: {item['why_mvp']}\n"

            msg += "\n**Cut Features:**\n"
            for item in res.get("cut_features", []):
                msg += f"- {item['feature']}: {item['why_cut']}\n"

            msg += f"\n**Risk Note:** {res.get('risk_note', 'N/A')}"
            await send_telegram_message(chat_id, msg)

        background_tasks.add_task(process_critique)

    elif text.startswith("/plan"):

        async def process_plan():
            res = await run_planner(team_id=team_id)
            msg = "📋 **Planner Tasks & Roadmap**:\n\n**Tasks:**\n"
            for task in res.get("tasks", []):
                msg += f"- {task['title']} (Assigned: {task['assigned_to']}) [Hour {task['target_hour']}]\n"

            msg += "\n**Milestones:**\n"
            for ms in res.get("roadmap", []):
                msg += f"- {ms['milestone']} (Hour {ms['target_hour']})\n"

            await send_telegram_message(chat_id, msg)

        background_tasks.add_task(process_plan)

    elif text.startswith("/pitch"):

        async def process_pitch():
            res = await run_pitch(team_id=team_id)
            msg = (
                f"🎤 **Pitch Outline**:\n\n"
                f"**Problem:** {res.get('problem')}\n"
                f"**Solution:** {res.get('solution')}\n\n"
                f"**What We Built:**\n"
                + "\n".join([f"- {item}" for item in res.get("what_we_built", [])])
            )
            await send_telegram_message(chat_id, msg)

        background_tasks.add_task(process_pitch)

    elif text.startswith("/blocker"):

        async def process_blocker():
            res = await run_blocker_check(team_id=team_id)
            if res.get("should_escalate"):
                msg = f"🚨 **BLOCKER ALERT**:\n{res.get('escalation_message')}"
            else:
                msg = "✅ No critical blockers reported!"
            await send_telegram_message(chat_id, msg)

        background_tasks.add_task(process_blocker)

    return {"status": "ok"}