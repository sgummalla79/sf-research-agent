"""
Skill management routes.

GET    /api/skills           — list all available skills with installed status
POST   /api/skills/{id}      — install a skill (creates user_agents + version 1)
DELETE /api/skills/{id}      — uninstall a skill
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request

from utils.auth import AuthUser, get_current_user

log    = logging.getLogger(__name__)
router = APIRouter(prefix="/api/skills")


@router.get("")
async def list_skills(request: Request, current_user: AuthUser = Depends(get_current_user)):
    db             = request.app.state.db
    skill_registry = request.app.state.skill_registry

    installed_ids = await db.user_skills.get_installed_skill_ids(current_user.sub)
    all_skills    = await db.skills.list_all()

    result = []
    for skill in all_skills:
        manifest = skill_registry.get(skill.skill_key).manifest if skill.skill_key in skill_registry else None
        result.append({
            "id":          skill.skill_key,   # string key, e.g. "architect"
            "skill_key":   skill.skill_key,
            "name":        skill.name,
            "description": skill.description,
            "icon":        skill.icon,
            "version":     skill.version,
            "installed":   skill.id in installed_ids,
            "pipeline":    manifest.pipeline if manifest else [],
        })

    return {"skills": result}


@router.post("/{skill_id}")
async def install_skill(
    skill_id:     str,
    request:      Request,
    current_user: AuthUser = Depends(get_current_user),
):
    db   = request.app.state.db
    skill = await db.skills.get_by_key(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found.")

    already = await db.user_skills.is_installed(current_user.sub, skill.id)
    if already:
        return {"ok": True, "skill": skill_id, "status": "already_installed"}

    # Install: create user_skills row + user_agents + version 1 for each agent
    await db.user_skills.install(current_user.sub, skill.id)
    agents = await db.agents.get_by_skill(skill.id)
    await db.user_agents.install_skill_agents(current_user.sub, agents)

    log.info("Installed skill '%s' for user %s (%d agents)", skill_id, current_user.sub, len(agents))
    return {"ok": True, "skill": skill_id, "status": "installed", "agents": len(agents)}


@router.delete("/{skill_id}")
async def uninstall_skill(
    skill_id:     str,
    request:      Request,
    current_user: AuthUser = Depends(get_current_user),
):
    db    = request.app.state.db
    skill = await db.skills.get_by_key(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found.")

    await db.user_skills.uninstall(current_user.sub, skill.id)
    return {"ok": True, "skill": skill_id}
