"""Small read-only HTTP API used by the Onyx Minecraft client mod."""

import logging
import os
from aiohttp import web

from src.database import databaseManager
from src.utils.loadConfig import listTiers

TIER_ORDER = {tier.lower(): index for index, tier in enumerate(listTiers) if tier.lower() != "none"}


def _highest(rows):
    if not rows:
        return None
    valid = [row for row in rows if str(row[2]).lower() in TIER_ORDER]
    if not valid:
        return None
    return max(valid, key=lambda row: TIER_ORDER[str(row[2]).lower()])


async def player_handler(request: web.Request) -> web.Response:
    username = request.match_info.get("username", "").strip()
    if not username or len(username) > 16:
        return web.json_response({"error": "invalid_username"}, status=400)

    try:
        rows = await databaseManager.getPlayerTierByMinecraftUsername(username)
    except Exception:
        logging.exception("Minecraft API database lookup failed")
        return web.json_response({"error": "database_error"}, status=500)

    best = _highest(rows)
    if best is None:
        return web.json_response({"error": "player_not_found"}, status=404)

    minecraft_username, minecraft_uuid, tier, kit, region, last_test = best
    kits = [
        {
            "kit": row[3],
            "tier": str(row[2]).upper(),
            "region": row[4],
            "last_test": row[5],
        }
        for row in rows
        if str(row[2]).lower() in TIER_ORDER
    ]

    return web.json_response({
        "username": minecraft_username,
        "uuid": minecraft_uuid,
        "highest_tier": str(tier).upper(),
        "emoji": "◆",
        "kit": kit,
        "region": region,
        "last_test": last_test,
        "kits": kits,
    })


async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "service": "onyx-minecraft-api"})


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/player/{username}", player_handler)
    app.router.add_get("/health", health_handler)
    return app


async def start_server():
    host = os.getenv("ONYX_API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("ONYX_API_PORT", "8080")))
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logging.info("Onyx Minecraft API listening on %s:%s", host, port)
    return runner
