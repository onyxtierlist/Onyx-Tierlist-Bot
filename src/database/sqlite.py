import sqlite3
import datetime
import os

def withConnection(func):
    async def wrapper(*args, **kwargs):
        os.makedirs("storage", exist_ok=True)
        connection = sqlite3.connect("storage/database.db")
        try:
            cursor = connection.cursor()
            result = await func(cursor, *args, **kwargs)
            connection.commit()
            return result
        except Exception as e:
            connection.rollback()
            print(e)
            return False
        finally:
            connection.close()
    return wrapper

@withConnection
async def createTables(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        discordID INTEGER PRIMARY KEY,
        minecraftUsername TEXT NOT NULL,
        minecraftUUID TEXT NOT NULL,
        tier TEXT NOT NULL,
        lastTest INTEGER NOT NULL,
        server TEXT NOT NULL,
        region TEXT NOT NULL,
        kit TEXT NOT NULL DEFAULT 'sword',
        restricted BOOLEAN NOT NULL DEFAULT 0
    )""")
    columns = [row[1] for row in cursor.execute("PRAGMA table_info(users)").fetchall()]
    if "kit" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN kit TEXT NOT NULL DEFAULT 'sword'")
    return True

@withConnection
async def addUser(cursor, discordID, minecraftUsername, minecraftUUID, tier, lastTest, server, region, kit):
    cursor.execute("""
    INSERT INTO users
      (discordID, minecraftUsername, minecraftUUID, tier, lastTest, server, region, kit, restricted)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(discordID) DO UPDATE SET
      minecraftUsername = excluded.minecraftUsername,
      minecraftUUID = excluded.minecraftUUID,
      server = excluded.server,
      region = excluded.region,
      kit = excluded.kit
    """, (discordID, minecraftUsername, minecraftUUID, tier, lastTest, server, region, kit, False))
    return True

@withConnection
async def getUserTicket(cursor, discordID):
    cursor.execute("SELECT minecraftUsername, tier, server, minecraftUUID, kit FROM users WHERE discordID = ?", (discordID,))
    return cursor.fetchone()

@withConnection
async def getResultInfo(cursor, discordID):
    cursor.execute("SELECT minecraftUsername, tier, region, kit FROM users WHERE discordID = ?", (discordID,))
    return cursor.fetchone()

@withConnection
async def addResult(cursor, discordID, tier):
    lastTest = int(datetime.datetime.now().timestamp())
    cursor.execute("UPDATE users SET tier = ?, lastTest = ? WHERE discordID = ?", (tier, lastTest, discordID))
    return True

@withConnection
async def userExists(cursor, discordID):
    cursor.execute("SELECT 1 FROM users WHERE discordID = ? LIMIT 1", (discordID,))
    return cursor.fetchone() is not None

@withConnection
async def getLastTest(cursor, discordID):
    cursor.execute("SELECT lastTest FROM users WHERE discordID = ?", (discordID,))
    return cursor.fetchone()

@withConnection
async def getTier(cursor, discordID):
    cursor.execute("SELECT tier FROM users WHERE discordID = ?", (discordID,))
    return cursor.fetchone()

@withConnection
async def isRestricted(cursor, discordID):
    cursor.execute("SELECT restricted FROM users WHERE discordID = ?", (discordID,))
    result = cursor.fetchone()
    return result[0] if result else False

@withConnection
async def updateUsername(cursor, discordID, username, uuid):
    cursor.execute("UPDATE users SET minecraftUsername = ?, minecraftUUID = ? WHERE discordID = ?", (username, uuid, discordID))
    return True

@withConnection
async def updateTier(cursor, discordID, tier):
    cursor.execute("UPDATE users SET tier = ? WHERE discordID = ?", (tier, discordID))
    return True

@withConnection
async def updateRestriction(cursor, discordID, restricted):
    cursor.execute("UPDATE users SET restricted = ? WHERE discordID = ?", (restricted, discordID))
    return True

@withConnection
async def getUserInfo(cursor, discordID):
    cursor.execute("SELECT minecraftUsername, tier, lastTest, region, restricted, minecraftUUID, kit FROM users WHERE discordID = ?", (discordID,))
    return cursor.fetchone()
