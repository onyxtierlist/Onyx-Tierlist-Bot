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

async def getUserTicket(discordID, kit): return await db.getUserTicket(discordID, kit)
async def getResultInfo(discordID, kit): return await db.getResultInfo(discordID, kit)
async def addResult(discordID, kit, tier): return await db.addResult(discordID, kit, tier)
async def userExists(discordID): return await db.userExists(discordID)
async def getLastTest(discordID, kit): return await db.getLastTest(discordID, kit)
async def getTier(discordID, kit): return await db.getTier(discordID, kit)
async def updateUsername(discordID, kit, username, uuid): return await db.updateUsername(discordID, kit, username, uuid)
async def updateTier(discordID, kit, tier): return await db.updateTier(discordID, kit, tier)
async def isRestriced(discordID): return await db.isRestricted(discordID=discordID)
async def updateRestriction(discordID, restricted): return await db.updateRestriction(discordID, restricted)
async def getUserInfo(discordID): return await db.getUserInfo(discordID)

async def getAllResults(): return await db.getAllResults()
