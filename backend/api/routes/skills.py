"""
Skills management routes — per user.

GET    /api/skills            — full directory (all discovered skills + installed flag)
POST   /api/skills/{id}       — install a skill (seeds default prompts for this user)
DELETE /api/skills/{id}       — uninstall a skill (removes from installed list only)
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from utils.auth import AuthUser, get_current_user

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
async def list_all_skills(
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    """Return every discovered skill with an `installed` boolean for this user."""
    db             = request.app.state.db
    skill_registry = request.app.state.skill_registry

    installed = await db.get_installed_skill_ids(current_user.sub)
    skills = [
        {
            "id":          skill.manifest.id,
            "name":        skill.manifest.name,
            "description": skill.manifest.description,
            "icon":        skill.manifest.icon,
            "installed":   skill.manifest.id in installed,
        }
        for skill in skill_registry.list_all()
    ]
    return {"skills": skills}


@router.post("/{skill_id}")
async def install_skill(
    skill_id: str,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    db             = request.app.state.db
    skill_registry = request.app.state.skill_registry

    try:
        skill = skill_registry.get(skill_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found.")

    await db.install_skill(current_user.sub, skill_id)

    # Seed default agent prompts if this user doesn't have any yet
    agent_keys = list(skill.all_agent_prompts.keys())
    if not await db.is_skill_seeded(current_user.sub, skill_id, agent_keys):
        await db.seed_flow_prompts(current_user.sub, skill_id, skill.all_agent_prompts)

    return {"ok": True, "skill_id": skill_id}


@router.delete("/{skill_id}")
async def uninstall_skill(
    skill_id: str,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    """
    Remove skill from user's installed list.
    Agent prompt versions are kept so existing sessions retain their snapshot
    references — they are simply orphaned, never deleted.
    """
    db = request.app.state.db
    await db.uninstall_skill(current_user.sub, skill_id)
    return {"ok": True, "skill_id": skill_id}
