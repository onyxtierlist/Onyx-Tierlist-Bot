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
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_kits (
        discordID INTEGER NOT NULL,
        kit TEXT NOT NULL,
        minecraftUsername TEXT NOT NULL,
        minecraftUUID TEXT NOT NULL,
        tier TEXT NOT NULL,
        lastTest INTEGER NOT NULL,
        server TEXT NOT NULL,
        region TEXT NOT NULL,
        PRIMARY KEY (discordID, kit),
        FOREIGN KEY (discordID) REFERENCES users(discordID)
    )""")
    cursor.execute("""
    INSERT OR IGNORE INTO user_kits
      (discordID, kit, minecraftUsername, minecraftUUID, tier, lastTest, server, region)
    SELECT discordID, kit, minecraftUsername, minecraftUUID, tier, lastTest, server, region
    FROM users
    """)
    # Migrate existing tier values to the canonical UPPERCASE format.
    cursor.execute("UPDATE users SET tier = UPPER(tier)")
    cursor.execute("UPDATE user_kits SET tier = UPPER(tier)")
    return True

@withConnection
async def addUser(cursor, discordID, minecraftUsername, minecraftUUID, tier, lastTest, server, region, kit):
    cursor.execute("""
    INSERT INTO users
        (discordID, minecraftUsername, minecraftUUID, tier, lastTest, server, region, kit, restricted)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(discordID) DO NOTHING
    """, (discordID, minecraftUsername, minecraftUUID, str(tier).strip().upper(), lastTest, server, region, kit, False))
    cursor.execute("""
    INSERT INTO user_kits
        (discordID, kit, minecraftUsername, minecraftUUID, tier, lastTest, server, region)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(discordID, kit) DO UPDATE SET
      minecraftUsername = excluded.minecraftUsername,
      minecraftUUID = excluded.minecraftUUID,
      server = excluded.server,
      region = excluded.region,
      kit = excluded.kit
    """, (discordID, kit, minecraftUsername, minecraftUUID, str(tier).strip().upper(), lastTest, server, region))
    return True

@withConnection
async def getUserTicket(cursor, discordID, kit):
    cursor.execute("SELECT minecraftUsername, tier, server, minecraftUUID, kit, region FROM user_kits WHERE discordID = ? AND kit = ?", (discordID, kit))
    return cursor.fetchone()

@withConnection
async def getResultInfo(cursor, discordID, kit):
    cursor.execute("SELECT minecraftUsername, tier, region, kit FROM user_kits WHERE discordID = ? AND kit = ?", (discordID, kit))
    return cursor.fetchone()

@withConnection
async def addResult(cursor, discordID, kit, tier):
    lastTest = int(datetime.datetime.now().timestamp())
    cursor.execute("UPDATE user_kits SET tier = ?, lastTest = ? WHERE discordID = ? AND kit = ?", (str(tier).strip().upper(), lastTest, discordID, kit))
    return True

@withConnection
async def userExists(cursor, discordID):
    cursor.execute("SELECT 1 FROM users WHERE discordID = ? LIMIT 1", (discordID,))
    return cursor.fetchone() is not None

@withConnection
async def getLastTest(cursor, discordID, kit):
    cursor.execute("SELECT lastTest FROM user_kits WHERE discordID = ? AND kit = ?", (discordID, kit))
    return cursor.fetchone()

@withConnection
async def getTier(cursor, discordID, kit):
    cursor.execute("SELECT tier FROM user_kits WHERE discordID = ? AND kit = ?", (discordID, kit))
    return cursor.fetchone()

@withConnection
async def isRestricted(cursor, discordID):
    cursor.execute("SELECT restricted FROM users WHERE discordID = ?", (discordID,))
    result = cursor.fetchone()
    return result[0] if result else False

@withConnection
async def updateUsername(cursor, discordID, kit, username, uuid):
    cursor.execute("UPDATE user_kits SET minecraftUsername = ?, minecraftUUID = ? WHERE discordID = ? AND kit = ?", (username, uuid, discordID, kit))
    return True

@withConnection
async def updateTier(cursor, discordID, kit, tier):
    cursor.execute("UPDATE user_kits SET tier = ? WHERE discordID = ? AND kit = ?", (str(tier).strip().upper(), discordID, kit))
    return True

@withConnection
async def updateRestriction(cursor, discordID, restricted):
    cursor.execute("UPDATE users SET restricted = ? WHERE discordID = ?", (restricted, discordID))
    return True

@withConnection
async def getUserInfo(cursor, discordID):
    cursor.execute("SELECT minecraftUsername, tier, lastTest, region, restricted, minecraftUUID, kit FROM users WHERE discordID = ?", (discordID,))
    return cursor.fetchone()

@withConnection
async def getAllResults(cursor):
    cursor.execute("SELECT discordID, kit, minecraftUsername, minecraftUUID, tier, lastTest, server, region FROM user_kits")
    return cursor.fetchall()

@withConnection
async def createSubtierTable(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subtiers (
        name TEXT PRIMARY KEY,
        createdAt INTEGER NOT NULL
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subtier_waitlist (
        discordID INTEGER NOT NULL,
        subtier TEXT NOT NULL,
        minecraftUsername TEXT NOT NULL,
        minecraftUUID TEXT NOT NULL,
        lastTest INTEGER NOT NULL DEFAULT 0,
        server TEXT NOT NULL,
        region TEXT NOT NULL,
        PRIMARY KEY (discordID, subtier)
    )""")
    return True

@withConnection
async def addSubtier(cursor, name):
    import time
    name = str(name).strip()
    cursor.execute("INSERT OR IGNORE INTO subtiers (name, createdAt) VALUES (?, ?)", (name, int(time.time())))
    return cursor.rowcount > 0

@withConnection
async def removeSubtier(cursor, name):
    name = str(name).strip()
    cursor.execute("DELETE FROM subtiers WHERE name = ?", (name,))
    cursor.execute("DELETE FROM subtier_waitlist WHERE subtier = ?", (name,))
    return cursor.rowcount >= 0

@withConnection
async def getSubtiers(cursor):
    cursor.execute("SELECT name FROM subtiers ORDER BY name COLLATE NOCASE")
    return [row[0] for row in cursor.fetchall()]

@withConnection
async def addSubtierUser(cursor, discordID, subtier, minecraftUsername, minecraftUUID, lastTest, server, region):
    cursor.execute("""
    INSERT INTO subtier_waitlist
      (discordID, subtier, minecraftUsername, minecraftUUID, lastTest, server, region)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(discordID, subtier) DO UPDATE SET
      minecraftUsername=excluded.minecraftUsername,
      minecraftUUID=excluded.minecraftUUID,
      server=excluded.server,
      region=excluded.region
    """, (discordID, subtier, minecraftUsername, minecraftUUID, lastTest, server, region))
    return True

@withConnection
async def getSubtierUser(cursor, discordID, subtier):
    cursor.execute("SELECT minecraftUsername, minecraftUUID, lastTest, server, region, subtier FROM subtier_waitlist WHERE discordID = ? AND subtier = ?", (discordID, subtier))
    return cursor.fetchone()

@withConnection
async def getSubtierResultInfo(cursor, discordID, subtier):
    cursor.execute("SELECT minecraftUsername, minecraftUUID, lastTest, server, region, subtier FROM subtier_waitlist WHERE discordID = ? AND subtier = ?", (discordID, subtier))
    return cursor.fetchone()

@withConnection
async def markSubtierTested(cursor, discordID, subtier):
    import time
    cursor.execute("UPDATE subtier_waitlist SET lastTest = ? WHERE discordID = ? AND subtier = ?", (int(time.time()), discordID, subtier))
    return cursor.rowcount > 0
