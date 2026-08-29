"""Secure synchronization of Discord tier results to the Onyx website."""
import asyncio
import logging
import os
import aiohttp

DEFAULT_URL = "https://onyx-website.onrender.com/api/integrations/discord/result"

async def sync_result(*, discord_id, minecraft_username, minecraft_uuid, region, kit, tier, tester):
    url = os.getenv("WEBSITE_API_URL", DEFAULT_URL).strip().rstrip("/")
    token = os.getenv("ONYX_INGEST_TOKEN", "").strip()
    if not url or not token:
        logging.warning("Website sync is not configured: WEBSITE_API_URL or ONYX_INGEST_TOKEN is missing.")
        return False

    payload = {
        "discordId": str(discord_id),
        "name": str(minecraft_username).strip(),
        "uuid": str(minecraft_uuid or "").replace("-", ""),
        "region": str(region or "—"),
        "kit": str(kit).strip().lower(),
        "rank": str(tier).strip().lower(),
        "tester": str(tester or "Discord"),
    }
    if not payload["name"] or payload["rank"] == "none":
        return False

    timeout = aiohttp.ClientTimeout(total=10)
    for attempt in range(1, 4):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url,
                    json=payload,
                    headers={"X-Onyx-Token": token, "Accept": "application/json"},
                ) as response:
                    detail = (await response.text())[:500]
                    if 200 <= response.status < 300:
                        logging.info("Website sync OK: %s / %s -> HTTP %s %s", payload["name"], payload["kit"], response.status, detail)
                        return True
                    logging.warning("Website sync failed attempt %s/3: HTTP %s %s", attempt, response.status, detail)
        except (aiohttp.ClientError, asyncio.TimeoutError, TimeoutError) as error:
            logging.warning("Website sync failed attempt %s/3: %s", attempt, error)
        if attempt < 3:
            await asyncio.sleep(attempt)
    return False
