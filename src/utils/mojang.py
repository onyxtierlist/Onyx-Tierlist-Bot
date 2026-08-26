import hashlib

import aiohttp


def offline_uuid(username: str) -> str:
    digest = bytearray(hashlib.md5(f"OfflinePlayer:{username}".encode("utf-8")).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30
    digest[8] = (digest[8] & 0x3F) | 0x80
    return digest.hex()

async def getuserid(username: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{username}") as response:
            if response.status == 200:
                data = await response.json()
                return str(data.get("id"))
            if response.status in (204, 404):
                return offline_uuid(username)
            else:
                return "8667ba71b85a4004af54457a9734eed7"