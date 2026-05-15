from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from repositories.base import BaseRepository


@dataclass
class UserAgent:
    id:              str
    user_id:         str
    agent_id:        str
    current_version: int
    provider_to_use: Optional[str]
    model_to_use:    Optional[str]
    created_at:      str


@dataclass
class UserAgentVersion:
    id:           str
    user_agent_id: str
    version:      int
    content:      str
    status:       str   # draft | published
    created_at:   str
    published_at: Optional[str]


class UserAgentRepository(BaseRepository):

    async def get(self, user_id: str, agent_id: str) -> Optional[UserAgent]:
        row = await self._fetchone(
            "SELECT id, user_id, agent_id, current_version, provider_to_use, model_to_use, created_at"
            " FROM user_agents WHERE user_id = %s AND agent_id = %s",
            (user_id, agent_id),
        )
        return self._row_to_ua(row) if row else None

    async def get_for_skill(self, user_id: str, skill_id: str) -> list[UserAgent]:
        rows = await self._fetchall(
            "SELECT ua.id, ua.user_id, ua.agent_id, ua.current_version,"
            "       ua.provider_to_use, ua.model_to_use, ua.created_at"
            " FROM user_agents ua"
            " JOIN agents a ON a.id = ua.agent_id"
            " WHERE ua.user_id = %s AND a.skill_id = %s",
            (user_id, skill_id),
        )
        return [self._row_to_ua(r) for r in rows]

    async def install_skill_agents(
        self,
        user_id:  str,
        agents:   list,   # list[Agent] from agent_repository
    ) -> None:
        """Create user_agents + version 1 (published) for each agent. Idempotent."""
        now = datetime.now(timezone.utc).isoformat()
        for agent in agents:
            # Insert user_agent row
            await self._exec(
                "INSERT INTO user_agents (user_id, agent_id, current_version, created_at)"
                " VALUES (%s, %s, 1, %s)"
                " ON CONFLICT (user_id, agent_id) DO NOTHING",
                (user_id, agent.id, now),
            )
            # Fetch the user_agent row to get its id
            ua_row = await self._fetchone(
                "SELECT id FROM user_agents WHERE user_id = %s AND agent_id = %s",
                (user_id, agent.id),
            )
            if not ua_row:
                continue
            ua_id = str(ua_row[0])
            # Insert version 1 as published
            await self._exec(
                "INSERT INTO user_agents_versions"
                " (user_agent_id, version, content, status, created_at, published_at)"
                " VALUES (%s, 1, %s, 'published', %s, %s)"
                " ON CONFLICT (user_agent_id, version) DO NOTHING",
                (ua_id, agent.default_content, now, now),
            )

    async def update_model(
        self,
        user_id:         str,
        agent_id:        str,
        provider_to_use: Optional[str],
        model_to_use:    Optional[str],
    ) -> None:
        await self._exec(
            "UPDATE user_agents SET provider_to_use = %s, model_to_use = %s"
            " WHERE user_id = %s AND agent_id = %s",
            (provider_to_use, model_to_use, user_id, agent_id),
        )

    async def get_current_content(self, user_agent_id: str) -> Optional[str]:
        row = await self._fetchone(
            "SELECT uav.content FROM user_agents_versions uav"
            " JOIN user_agents ua ON ua.id = uav.user_agent_id"
            " WHERE uav.user_agent_id = %s AND uav.version = ua.current_version",
            (user_agent_id,),
        )
        return row[0] if row else None

    async def save_draft(
        self,
        user_id:   str,
        agent_id:  str,
        content:   str,
    ) -> UserAgentVersion:
        """Save or update draft. At most one draft per user_agent at a time."""
        now = datetime.now(timezone.utc).isoformat()
        ua = await self.get(user_id, agent_id)
        if not ua:
            raise ValueError(f"No user_agent found for user={user_id} agent={agent_id}")

        # Check for existing draft
        existing = await self._fetchone(
            "SELECT id FROM user_agents_versions"
            " WHERE user_agent_id = %s AND status = 'draft'",
            (ua.id,),
        )
        if existing:
            await self._exec(
                "UPDATE user_agents_versions SET content = %s, created_at = %s WHERE id = %s",
                (content, now, str(existing[0])),
            )
        else:
            max_row = await self._fetchone(
                "SELECT MAX(version) FROM user_agents_versions WHERE user_agent_id = %s",
                (ua.id,),
            )
            next_ver = (max_row[0] or 0) + 1
            await self._exec(
                "INSERT INTO user_agents_versions"
                " (user_agent_id, version, content, status, created_at)"
                " VALUES (%s, %s, %s, 'draft', %s)",
                (ua.id, next_ver, content, now),
            )
        return await self._get_draft(ua.id)

    async def discard_draft(self, user_id: str, agent_id: str) -> None:
        ua = await self.get(user_id, agent_id)
        if not ua:
            return
        await self._exec(
            "DELETE FROM user_agents_versions WHERE user_agent_id = %s AND status = 'draft'",
            (ua.id,),
        )

    async def publish(self, user_id: str, agent_id: str) -> UserAgentVersion:
        """Publish the current draft. Updates current_version pointer."""
        now = datetime.now(timezone.utc).isoformat()
        ua = await self.get(user_id, agent_id)
        if not ua:
            raise ValueError(f"No user_agent found for user={user_id} agent={agent_id}")

        draft = await self._get_draft(ua.id)
        if not draft:
            raise ValueError(f"No draft to publish for agent={agent_id}")

        await self._exec(
            "UPDATE user_agents_versions SET status = 'published', published_at = %s WHERE id = %s",
            (now, draft.id),
        )
        await self._exec(
            "UPDATE user_agents SET current_version = %s WHERE id = %s",
            (draft.version, ua.id),
        )
        return draft

    async def publish_all(self, user_id: str, skill_id: str) -> list[UserAgentVersion]:
        """Publish all drafts for a skill. Returns list of published versions."""
        user_agents = await self.get_for_skill(user_id, skill_id)
        published = []
        for ua in user_agents:
            draft = await self._get_draft(ua.id)
            if draft:
                published.append(await self.publish(user_id, ua.agent_id))
        return published

    async def get_version_history(self, user_id: str, agent_id: str) -> list[UserAgentVersion]:
        ua = await self.get(user_id, agent_id)
        if not ua:
            return []
        rows = await self._fetchall(
            "SELECT id, user_agent_id, version, content, status, created_at, published_at"
            " FROM user_agents_versions WHERE user_agent_id = %s ORDER BY version DESC",
            (ua.id,),
        )
        return [self._row_to_uav(r) for r in rows]

    async def _get_draft(self, user_agent_id: str) -> Optional[UserAgentVersion]:
        row = await self._fetchone(
            "SELECT id, user_agent_id, version, content, status, created_at, published_at"
            " FROM user_agents_versions WHERE user_agent_id = %s AND status = 'draft'",
            (user_agent_id,),
        )
        return self._row_to_uav(row) if row else None

    @staticmethod
    def _row_to_ua(row) -> UserAgent:
        return UserAgent(
            id=str(row[0]), user_id=row[1], agent_id=str(row[2]),
            current_version=row[3], provider_to_use=row[4], model_to_use=row[5],
            created_at=str(row[6]),
        )

    @staticmethod
    def _row_to_uav(row) -> UserAgentVersion:
        return UserAgentVersion(
            id=str(row[0]), user_agent_id=str(row[1]), version=row[2],
            content=row[3], status=row[4], created_at=str(row[5]),
            published_at=str(row[6]) if row[6] else None,
        )
