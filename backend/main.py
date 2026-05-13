"""
Development helper — quick CLI to start or resume a session without the Vue UI.
For production use, run the FastAPI server instead: uvicorn api.app:app --reload

Usage:
  python main.py --brief "We need to design our cloud architecture..."
  python main.py --session-id <id> --reply "500 users, Sales Cloud only."
"""

import argparse
import asyncio
import uuid
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from framework.engine import SkillEngine
from framework.registry import SkillRegistry
from persistence.checkpointer import get_async_checkpointer
from state import AgentState

_SKILLS_DIR = Path(__file__).parent / "skills"
_DEFAULT_SKILL = "architect"


def print_sep():
    print("\n" + "=" * 70 + "\n")


async def run(brief: str = "", session_id: str = "", reply: str = ""):
    async with get_async_checkpointer() as db:
        registry = SkillRegistry(_SKILLS_DIR)
        registry.load_all()
        skill  = registry.get(_DEFAULT_SKILL)
        graph  = SkillEngine().build(skill, db.checkpointer)

        if not session_id:
            session_id = str(uuid.uuid4())
            print(f"New session: {session_id}")
            print_sep()
            initial_state = AgentState(
                session_id    = session_id,
                project_brief = brief,
                flow_config   = dict(skill.all_agent_prompts),
            )
            config = {"configurable": {"thread_id": session_id}}
            state  = await graph.ainvoke(initial_state, config)
        else:
            print(f"Resuming session: {session_id}")
            print_sep()
            config = {"configurable": {"thread_id": session_id}}
            state  = await graph.ainvoke(
                Command(resume=reply) if reply else {"messages": [HumanMessage(content=reply)]},
                config,
            )

        print_sep()
        print(f"Stage:    {state['current_stage']}")
        print(f"Session:  {session_id}  ← save this to resume")
        print(f"Doc v{state.get('document_version', 0)}, revision {state.get('revision_count', 0)}")
        print_sep()

        messages = state.get("messages", [])
        if messages:
            print("Last agent message:")
            print(messages[-1].content)

        if state["current_stage"] == "complete":
            print_sep()
            print("APPROVED — Final document:")
            print_sep()
            print(state.get("document_draft", ""))
        elif state["current_stage"] == "halted":
            print_sep()
            print("HALTED — Maximum revisions reached. Human review required.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prajna CLI")
    parser.add_argument("--brief",      default="", help="Initial project brief (new session)")
    parser.add_argument("--session-id", default="", help="Resume an existing session")
    parser.add_argument("--reply",      default="", help="Your answer to the agent's question")
    args = parser.parse_args()

    if not args.session_id and not args.brief:
        parser.error("Provide --brief for a new session or --session-id + --reply to resume.")

    asyncio.run(run(brief=args.brief, session_id=args.session_id, reply=args.reply))
