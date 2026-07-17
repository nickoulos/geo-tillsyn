"""Flip the seeded e2e-mock completion model to supports_tool_calling=True.

eneo's e2e seed creates the mock model with tool calling disabled; MCP tools
are only offered to models that support it. Run inside the e2e-backend
container after startup:

  docker compose -f docker-compose.e2e.yml -f .../docker-compose.mcp-live.yml \
    exec e2e-backend bash -lc \
    'PATH=/workspace/backend/.venv/bin:$PATH python /spike/seed_tool_support.py'

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import asyncio

from sqlalchemy import update

from eneo.database.database import sessionmanager
from eneo.database.tables.ai_models_table import CompletionModels
from eneo.main.config import get_settings

MODEL_NAME = "e2e-mock"


async def main() -> None:
    sessionmanager.init(get_settings().database_url)
    async with sessionmanager.session() as session, session.begin():
        result = await session.execute(
            update(CompletionModels)
            .where(CompletionModels.name == MODEL_NAME)
            .values(supports_tool_calling=True)
        )
        print(
            f"[seed_tool_support] rows updated: {result.rowcount} "
            f"({MODEL_NAME} -> supports_tool_calling=True)",
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(main())
