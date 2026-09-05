import aiomysql
import datetime
from src.utils.loadConfig import mysqlInfo

MYSQL_CONFIG = {
    "host": mysqlInfo["host"],
    "port": mysqlInfo["port"],
    "user": mysqlInfo["user"],
    "password": mysqlInfo["password"],
    "db": mysqlInfo["database"],
    "autocommit": False,
}

def withConnection(func):
    async def wrapper(*args, **kwargs):
        connection = await aiomysql.connect(**MYSQL_CONFIG)
        try:
            async with connection.cursor() as cursor:
                result = await func(cursor, *args, **kwargs)
                await connection.commit()
                return result
        except Exception as e:
            await connection.rollback()
            print(e)
            return False
        finally:
            connection.close()

    return wrapper

@withConnection
async def createTables(cursor):
    await cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        discordID BIGINT PRIMARY KEY,
        minecraftUsername VARCHAR(255) NOT NULL,
        minecraftUUID VARCHAR(255) NOT NULL,
        tier VARCHAR(50) NOT NULL,
        lastTest BIGINT NOT NULL,
        server VARCHAR(255) NOT NULL,
        region VARCHAR(255) NOT NULL,
        kit VARCHAR(50) NOT NULL DEFAULT 'sword',
        restricted BOOLEAN NOT NULL DEFAULT FALSE
    )
    """)
    await cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_kits (
        discordID BIGINT NOT NULL,
        kit VARCHAR(50) NOT NULL,
        minecraftUsername VARCHAR(255) NOT NULL,
        minecraftUUID VARCHAR(255) NOT NULL,
        tier VARCHAR(50) NOT NULL,
        lastTest BIGINT NOT NULL,
        server VARCHAR(255) NOT NULL,
        region VARCHAR(255) NOT NULL,
        PRIMARY KEY (discordID, kit),
        FOREIGN KEY (discordID) REFERENCES users(discordID)
    )
    """)
    await cursor.execute("""
    INSERT IGNORE INTO user_kits
      (discordID, kit, minecraftUsername, minecraftUUID, tier, lastTest, server, region)
    SELECT discordID, kit, minecraftUsername, minecraftUUID, tier, lastTest, server, region
    FROM users
    """)
    # Migrate existing tier values to the canonical UPPERCASE format.
    await cursor.execute("UPDATE users SET tier = UPPER(tier)")
    await cursor.execute("UPDATE user_kits SET tier = UPPER(tier)")
    return True

@withConnection
async def addUser(cursor, discordID, minecraftUsername, minecraftUUID, tier, lastTest, server, region, kit):
    await cursor.execute("""
    INSERT IGNORE INTO users
        (discordID, minecraftUsername, minecraftUUID, tier, lastTest, server, region, kit, restricted)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (discordID, minecraftUsername, minecraftUUID, str(tier).strip().upper(), lastTest, server, region, kit, False))
    await cursor.execute("""
    INSERT INTO user_kits
        (discordID, kit, minecraftUsername, minecraftUUID, tier, lastTest, server, region)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      minecraftUsername = VALUES(minecraftUsername),
      minecraftUUID = VALUES(minecraftUUID),
      server = VALUES(server),
      region = VALUES(region),
      kit = VALUES(kit)
    """, (discordID, kit, minecraftUsername, minecraftUUID, str(tier).strip().upper(), lastTest, server, region))
    return True

@withConnection
async def getUserTicket(cursor, discordID, kit):
    await cursor.execute("SELECT minecraftUsername, tier, server, minecraftUUID, kit, region FROM user_kits WHERE discordID = %s AND kit = %s", (discordID, kit))
    return await cursor.fetchone()

@withConnection
async def getResultInfo(cursor, discordID, kit):
    await cursor.execute("SELECT minecraftUsername, tier, region, kit FROM user_kits WHERE discordID = %s AND kit = %s", (discordID, kit))
    return await cursor.fetchone()

@withConnection
async def addResult(cursor, discordID, kit, tier):
    lastTest = int(datetime.datetime.now().timestamp())
    await cursor.execute("UPDATE user_kits SET tier = %s, lastTest = %s WHERE discordID = %s AND kit = %s", (str(tier).strip().upper(), lastTest, discordID, kit))
    return True

@withConnection
async def userExists(cursor, discordID):
    await cursor.execute("SELECT 1 FROM users WHERE discordID = %s LIMIT 1", (discordID,))
    return (await cursor.fetchone()) is not None

@withConnection
async def isRestricted(cursor, discordID):
    await cursor.execute("SELECT restricted FROM users WHERE discordID = %s", (discordID,))
    result = await cursor.fetchone()
    return result[0] if result else False

@withConnection
async def getLastTest(cursor, discordID, kit):
    await cursor.execute("SELECT lastTest FROM user_kits WHERE discordID = %s AND kit = %s", (discordID, kit))
    return await cursor.fetchone()

@withConnection
async def getTier(cursor, discordID, kit):
    await cursor.execute("SELECT tier FROM user_kits WHERE discordID = %s AND kit = %s", (discordID, kit))
    return await cursor.fetchone()

@withConnection
async def updateUsername(cursor, discordID, kit, username, uuid):
    await cursor.execute("UPDATE user_kits SET minecraftUsername = %s, minecraftUUID = %s WHERE discordID = %s AND kit = %s", (username, uuid, discordID, kit))
    return True

@withConnection
async def updateTier(cursor, discordID, kit, tier):
    await cursor.execute("UPDATE user_kits SET tier = %s WHERE discordID = %s AND kit = %s", (str(tier).strip().upper(), discordID, kit))
    return True

@withConnection
async def updateRestriction(cursor, discordID, restricted):
    await cursor.execute("UPDATE users SET restricted = %s WHERE discordID = %s", (restricted, discordID))
    return True

@withConnection
async def getUserInfo(cursor, discordID):
    await cursor.execute("SELECT minecraftUsername, tier, lastTest, region, restricted, minecraftUUID, kit FROM users WHERE discordID = %s", (discordID,))
    return await cursor.fetchone()

@withConnection
async def getAllResults(cursor):
    await cursor.execute("SELECT discordID, kit, minecraftUsername, minecraftUUID, tier, lastTest, server, region FROM user_kits")
    return await cursor.fetchall()

@withConnection
async def createSubtierTable(cursor):
    await cursor.execute("""
    CREATE TABLE IF NOT EXISTS subtiers (
        name VARCHAR(100) PRIMARY KEY,
        createdAt BIGINT NOT NULL
    )
    """)
    await cursor.execute("""
    CREATE TABLE IF NOT EXISTS subtier_waitlist (
        discordID BIGINT NOT NULL,
        subtier VARCHAR(100) NOT NULL,
        minecraftUsername VARCHAR(255) NOT NULL,
        minecraftUUID VARCHAR(255) NOT NULL,
        lastTest BIGINT NOT NULL DEFAULT 0,
        server VARCHAR(255) NOT NULL,
        region VARCHAR(255) NOT NULL,
        PRIMARY KEY (discordID, subtier)
    )
    """)
    return True

@withConnection
async def addSubtier(cursor, name):
    import time
    await cursor.execute("INSERT IGNORE INTO subtiers (name, createdAt) VALUES (%s, %s)", (str(name).strip(), int(time.time())))
    return cursor.rowcount > 0

@withConnection
async def removeSubtier(cursor, name):
    name = str(name).strip()
    await cursor.execute("DELETE FROM subtiers WHERE name = %s", (name,))
    await cursor.execute("DELETE FROM subtier_waitlist WHERE subtier = %s", (name,))
    return True

@withConnection
async def getSubtiers(cursor):
    await cursor.execute("SELECT name FROM subtiers ORDER BY name")
    return [row[0] for row in await cursor.fetchall()]

@withConnection
async def addSubtierUser(cursor, discordID, subtier, minecraftUsername, minecraftUUID, lastTest, server, region):
    await cursor.execute("""
    INSERT INTO subtier_waitlist
      (discordID, subtier, minecraftUsername, minecraftUUID, lastTest, server, region)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      minecraftUsername=VALUES(minecraftUsername),
      minecraftUUID=VALUES(minecraftUUID),
      server=VALUES(server),
      region=VALUES(region)
    """, (discordID, subtier, minecraftUsername, minecraftUUID, lastTest, server, region))
    return True

@withConnection
async def getSubtierUser(cursor, discordID, subtier):
    await cursor.execute("SELECT minecraftUsername, minecraftUUID, lastTest, server, region, subtier FROM subtier_waitlist WHERE discordID = %s AND subtier = %s", (discordID, subtier))
    return await cursor.fetchone()

@withConnection
async def getSubtierResultInfo(cursor, discordID, subtier):
    await cursor.execute("SELECT minecraftUsername, minecraftUUID, lastTest, server, region, subtier FROM subtier_waitlist WHERE discordID = %s AND subtier = %s", (discordID, subtier))
    return await cursor.fetchone()

@withConnection
async def markSubtierTested(cursor, discordID, subtier):
    import time
    await cursor.execute("UPDATE subtier_waitlist SET lastTest = %s WHERE discordID = %s AND subtier = %s", (int(time.time()), discordID, subtier))
    return cursor.rowcount > 0
