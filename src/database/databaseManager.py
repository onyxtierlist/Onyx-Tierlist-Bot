from src.utils.loadConfig import databaseType

if databaseType == "mysql":
    from src.database import mysql as db
elif databaseType == "sqlite":
    from src.database import sqlite as db
else:
    raise ValueError(f"Unsupported database type: {databaseType}")

async def createTables(): return await db.createTables()

async def addUser(discordID, minecraftUsername, minecraftUUID, tier, lastTest, server, region, kit):
    return await db.addUser(discordID, minecraftUsername, minecraftUUID, tier, lastTest, server, region, kit)

async def getUserTicket(discordID): return await db.getUserTicket(discordID)
async def getResultInfo(discordID): return await db.getResultInfo(discordID)
async def addResult(discordID, tier): return await db.addResult(discordID, tier)
async def userExists(discordID): return await db.userExists(discordID)
async def getLastTest(discordID): return await db.getLastTest(discordID)
async def getTier(discordID): return await db.getTier(discordID)
async def updateUsername(discordID, username, uuid): return await db.updateUsername(discordID, username, uuid)
async def updateTier(discordID, tier): return await db.updateTier(discordID, tier)
async def isRestriced(discordID): return await db.isRestricted(discordID=discordID)
async def updateRestriction(discordID, restricted): return await db.updateRestriction(discordID, restricted)
async def getUserInfo(discordID): return await db.getUserInfo(discordID)
