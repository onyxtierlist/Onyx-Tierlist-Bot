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
    return True

@withConnection
async def addUser(cursor, discordID, minecraftUsername, minecraftUUID, tier, lastTest, server, region, kit):
    await cursor.execute("""
    INSERT INTO users
      (discordID, minecraftUsername, minecraftUUID, tier, lastTest, server, region, kit, restricted)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      minecraftUsername = VALUES(minecraftUsername),
      minecraftUUID = VALUES(minecraftUUID),
      server = VALUES(server),
      region = VALUES(region),
      kit = VALUES(kit)
    """, (discordID, minecraftUsername, minecraftUUID, tier, lastTest, server, region, kit, False))
    return True

@withConnection
async def getUserTicket(cursor, discordID):
    await cursor.execute("SELECT minecraftUsername, tier, server, minecraftUUID, kit FROM users WHERE discordID = %s", (discordID,))
    return await cursor.fetchone()

@withConnection
async def getResultInfo(cursor, discordID):
    await cursor.execute("SELECT minecraftUsername, tier, region, kit FROM users WHERE discordID = %s", (discordID,))
    return await cursor.fetchone()

@withConnection
async def addResult(cursor, discordID, tier):
    lastTest = int(datetime.datetime.now().timestamp())
    await cursor.execute("UPDATE users SET tier = %s, lastTest = %s WHERE discordID = %s", (tier, lastTest, discordID))
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
async def getLastTest(cursor, discordID):
    await cursor.execute("SELECT lastTest FROM users WHERE discordID = %s", (discordID,))
    return await cursor.fetchone()

@withConnection
async def getTier(cursor, discordID):
    await cursor.execute("SELECT tier FROM users WHERE discordID = %s", (discordID,))
    return await cursor.fetchone()

@withConnection
async def updateUsername(cursor, discordID, username, uuid):
    await cursor.execute("UPDATE users SET minecraftUsername = %s, minecraftUUID = %s WHERE discordID = %s", (username, uuid, discordID))
    return True

@withConnection
async def updateTier(cursor, discordID, tier):
    await cursor.execute("UPDATE users SET tier = %s WHERE discordID = %s", (tier, discordID))
    return True

@withConnection
async def updateRestriction(cursor, discordID, restricted):
    await cursor.execute("UPDATE users SET restricted = %s WHERE discordID = %s", (restricted, discordID))
    return True

@withConnection
async def getUserInfo(cursor, discordID):
    await cursor.execute("SELECT minecraftUsername, tier, lastTest, region, restricted, minecraftUUID, kit FROM users WHERE discordID = %s", (discordID,))
    return await cursor.fetchone()
