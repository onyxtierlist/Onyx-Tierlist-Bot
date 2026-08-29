"""Secure, best-effort synchronization of Discord test results to the Onyx website."""

import logging
import os

import aiohttp


async def sync_result(*, discord_id, minecraft_username, minecraft_uuid, region, kit, tier, tester):
    """POST a completed result to the website without breaking Discord on failure."""
    url = os.getenv("WEBSITE_API_URL", "").strip().rstrip("/")
    token = os.getenv("ONYX_INGEST_TOKEN", "").strip()
    if not url or not token:
        logging.info("Website result sync is not configured; skipping.")
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

    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url,
                json=payload,
                headers={
                    "X-Onyx-Token": token,
                    "Accept": "application/json",
                },
            ) as response:
                if response.status < 200 or response.status >= 300:
                    detail = (await response.text())[:500]
                    logging.warning(
                        "Website result sync failed with HTTP %s: %s",
                        response.status,
                        detail,
                    )
                    return False
    except (aiohttp.ClientError, TimeoutError) as error:
        logging.warning("Website result sync failed: %s", error)
        return False

    logging.info("Synced %s's %s result to the website.", payload["name"], payload["kit"])
    return True
