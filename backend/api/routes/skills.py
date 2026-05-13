"""
Skills management routes.

GET  /api/skills            — full directory (all discovered skills + installed flag)
POST /api/skills/{id}       — install a skill
DELETE /api/skills/{id}     — uninstall a skill
"""

from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
async def list_all_skills(request: Request) -> dict:
    """Return every discovered skill with an `installed` boolean."""
    db             = request.app.state.db
    skill_registry = request.app.state.skill_registry

    installed = await db.get_installed_skill_ids()
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
async def install_skill(skill_id: str, request: Request) -> dict:
    db             = request.app.state.db
    skill_registry = request.app.state.skill_registry

    try:
        skill_registry.get(skill_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found.")

    await db.install_skill(skill_id)
    return {"ok": True, "skill_id": skill_id}


@router.delete("/{skill_id}")
async def uninstall_skill(skill_id: str, request: Request) -> dict:
    db = request.app.state.db
    await db.uninstall_skill(skill_id)
    return {"ok": True, "skill_id": skill_id}
