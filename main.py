import os
import sys
import logging
import time
import asyncio

from aiohttp import web

import nextcord
from nextcord.ext import commands, tasks
from dotenv import load_dotenv

from src.utils import mojang, format
from src.tierlistQueue import TierlistQueue
from src.ui.waitlistButton import WaitlistButton, WaitlistForm
from src.ui.enterQueueButton import EnterQueueButton
from src.ui.closeTicketButton import CloseTicketButton
from src.database import databaseManager
from src.utils.loadConfig import *
listQueueChannel = [
    kit_data["queue_channel"]
    for kit_data in listKits.values()
]

try:
    os.makedirs("logs", exist_ok=True)
    os.makedirs("storage", exist_ok=True)
except Exception as e:
    print(f"Uanble to create logs/storage directory: ", e)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
        handlers=[
        logging.FileHandler(f"logs/logs-{time.time()}.log")  # This logs to a file
    ]
)

load_dotenv()

intents = nextcord.Intents.all()
bot = commands.Bot(intents=intents)
queue_message_lock = asyncio.Lock()

TIER_ORDER = ["ht1", "lt1", "ht2", "lt2", "ht3", "lt3", "ht4", "lt4", "ht5", "lt5"]
TIER_EMOJIS = {
    "ht1": "👑", "lt1": "💎", "ht2": "🔥", "lt2": "⚡", "ht3": "⭐",
    "lt3": "✦", "ht4": "◆", "lt4": "◇", "ht5": "●", "lt5": "○",
}
api_runner = None

async def api_player(request):
    username = request.match_info["username"].strip()
    if not username:
        return web.json_response({"error": "missing username"}, status=400)

    rows = await databaseManager.getMinecraftPlayerKits(username)
    tiers = []
    for row in rows or []:
        tier = str(row[0]).lower()
        if tier in TIER_ORDER:
            tiers.append(tier)

    if not tiers:
        return web.json_response({
            "found": False,
            "highest_tier": "none",
            "emoji": ""
        })

    highest = min(tiers, key=TIER_ORDER.index)
    return web.json_response({
        "found": True,
        "highest_tier": highest,
        "emoji": TIER_EMOJIS[highest]
    })

async def start_http_api():
    global api_runner
    if api_runner is not None:
        return

    app = web.Application()
    app.router.add_get("/api/player/{username}", api_player)
    api_runner = web.AppRunner(app)
    await api_runner.setup()

    port = int(os.getenv("PORT", os.getenv("API_PORT", "8080")))
    site = web.TCPSite(api_runner, "0.0.0.0", port)
    await site.start()
    logging.info("Onyx Tier API listening on port %s", port)



try:
    queue = TierlistQueue(
        maxQueue=maxQueue,
        maxTesters=maxTester,
        cooldown=cooldown,
    )
    queue.setup(listKits)

except Exception:
    logging.exception("Setting up queue failed")
    print("Setting up queue failed. Check the latest file in the logs folder.")
    raise

def is_me(m):
    return m.author == bot.user

async def notify_queue(channel, embed_data):
    await channel.send(
        content="@here",
        embed=nextcord.Embed.from_dict(embed_data),
        allowed_mentions=nextcord.AllowedMentions(everyone=True),
    )

async def update_queue_message(queue_key, embed_data, view):
    """Keep one message as the current queue message for a kit."""
    async with queue_message_lock:
        data = queue.getqueueraw()[queue_key]
        channel = bot.get_channel(data["queueChannel"])
        if channel is None:
            raise RuntimeError(f"Queue channel for kit '{queue_key}' was not found.")

        message_id = data["queueMessage"]
        if message_id is not None:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(
                    content="@here",
                    embed=nextcord.Embed.from_dict(embed_data),
                    view=view,
                )
                return
            except nextcord.NotFound:
                pass

        queue_message = await channel.send(
            content="@here",
            embed=nextcord.Embed.from_dict(embed_data),
            view=view,
            allowed_mentions=nextcord.AllowedMentions(everyone=True),
        )
        queue.addQueueMessageId(queue_key, queue_message.id)

async def refresh_queue_message(queue_key):
    await update_queue_message(
        queue_key,
        queue.makeQueueMessage(queue_key),
        EnterQueueButton(queue, refresh_queue_message),
    )

async def setupBot():
    await databaseManager.createTables()
    waitlist_channel_id = channels["enterWaitlist"]
    waitlist_channel = bot.get_channel(waitlist_channel_id)
    if waitlist_channel is None:
        raise RuntimeError(
            f"Configured waitlist channel {waitlist_channel_id} was not found. "
            "Check config/config.yml and the bot's server access."
        )

    await waitlist_channel.purge(limit=10, check=is_me)
    await waitlist_channel.send(embed=nextcord.Embed.from_dict(format.enterwaitlistmessage), view=WaitlistButton())
    for kit, kit_data in listKits.items():
        queue_channel_id = int(kit_data["queue_channel"])

        channel = bot.get_channel(queue_channel_id)

        if channel is None:
            try:
                channel = await bot.fetch_channel(queue_channel_id)
            except (nextcord.NotFound, nextcord.Forbidden, nextcord.HTTPException) as error:
                raise RuntimeError(
                    f"Queue channel {queue_channel_id} for kit '{kit}' "
                    "does not exist or the bot cannot access it."
                ) from error

        await channel.purge(limit=10, check=is_me)
        await channel.send(
            embed=nextcord.Embed.from_dict(format.formatnoqueue())
        )


@bot.slash_command(name="waitlist", description="joins the evaluation waitlist")
async def waitlist(
    interaction: nextcord.Interaction,
    kit: str = nextcord.SlashOption(
        description="Choose the kit you want to test",
        required=True,
        choices=listKitsText,
    ),
):
    await interaction.response.send_modal(WaitlistForm(kit))
    
    
@bot.event
async def on_ready():
    print(f"Tier Testing bot has logged online ✅")
    try:
        await setupBot()
        await start_http_api()
        if not updateQueue.is_running():
            updateQueue.start()
    except Exception as e:
        logging.exception("Failed bot startup sequence: ")
        sys.exit("Failed startup sequence")

@tasks.loop(seconds=reloadQueue)
async def updateQueue():
    for queue_key, data in queue.getqueueraw().items():
        if not data["open"] or data["queueMessage"] is None:
            continue

        channel = bot.get_channel(data["queueChannel"])
        if channel is None:
            logging.warning(
                "Queue channel %s for kit %s is unavailable.",
                data["queueChannel"],
                queue_key,
            )
            continue

        embed_data = queue.makeQueueMessage(queue_key=queue_key)

        try:
            message = await channel.fetch_message(data["queueMessage"])
            await message.edit(
                embed=nextcord.Embed.from_dict(embed_data)
            )

        except nextcord.NotFound:
            logging.warning(
                "Queue message for kit %s was deleted. Creating a replacement.",
                queue_key,
            )

            replacement = await channel.send(
                embed=nextcord.Embed.from_dict(embed_data),
                view=EnterQueueButton(queue, refresh_queue_message),
            )

            queue.addQueueMessageId(queue_key, replacement.id)

        except nextcord.Forbidden:
            logging.exception(
                "The bot cannot access the queue channel for kit %s.",
                queue_key,
            )

        except nextcord.HTTPException:
            logging.exception(
                "Failed to update the queue message for kit %s.",
                queue_key,
            )



@bot.slash_command(name="results", description="closes a ticket and gives a tier to a user")
async def results(
    interaction: nextcord.Interaction,
    user: nextcord.User = nextcord.SlashOption(
        description="Enter their discord account",
        required=True,
    ),
    newtier: str = nextcord.SlashOption(
        description="Enter their new tier",
        required=True,
        choices=listTiers
    ),
    kit: str = nextcord.SlashOption(
        description="Choose the kit the result is for",
        required=True,
        choices=listKitsText,
    )
    ):
    try:
        await interaction.response.defer(ephemeral=True)
        if testerRole not in [role.id for role in interaction.user.roles]: await interaction.followup.send(messages["noPermission"], ephemeral=True); return
        
        exists = await databaseManager.userExists(user.id)
        if not exists: await interaction.followup.send("User does not exist in the database", ephemeral=True); return
        
        isrestricted = await databaseManager.isRestriced(interaction.user.id)
        if isrestricted: await interaction.followup.send(content="User is currently restricted", ephemeral=True); return

        restricted = await databaseManager.isRestriced(user.id)
        if restricted: await interaction.followup.send("User is restricted", ephemeral=True); return

        username, oldtier, region, saved_kit = await databaseManager.getResultInfo(user.id, kit)
        if username is None:
            await interaction.followup.send(
                f"That user is not registered for the {kit} waitlist.", ephemeral=True
            )
            return

        uuid = await mojang.getuserid(username=username)

        result_embed_data = format.formatresult(discordUsername=user.name, testerID=interaction.user.id, region=region, kit=saved_kit, minecraftUsername=username, oldTier=oldtier, newTier=newtier, uuid=uuid)
        embed = nextcord.Embed.from_dict(result_embed_data)

        await databaseManager.addResult(discordID=user.id, kit=kit, tier=newtier)

        member = interaction.guild.get_member(user.id)
        if member is None:
            raise RuntimeError(f"User {user.id} is not in the server.")

        waitlist_role_id = int(listKits[kit].get("waitlist_role", 0) or 0)
        waitlist_role = interaction.guild.get_role(waitlist_role_id) if waitlist_role_id else None
        if waitlist_role and waitlist_role in member.roles:
            await member.remove_roles(waitlist_role, reason=f"{kit} result recorded")

        region_roles_to_remove = [role for role in member.roles if role.id in listRegionRolePing]
        if region_roles_to_remove:
            await member.remove_roles(*region_roles_to_remove, reason="Region roles removed by /results command")

        configured_tier_role_ids = set(listTierRoles.values())
        for kit_tier_roles in listKitTierRoles.values():
            configured_tier_role_ids.update(
                role_id for role_id in kit_tier_roles.values() if role_id
            )
        tier_roles_to_remove = [
            role for role in member.roles if role.id in configured_tier_role_ids
        ]
        if tier_roles_to_remove:
            await member.remove_roles(*tier_roles_to_remove, reason="Old tier roles removed by /results command")
        
        kit_tier_roles = listKitTierRoles.get(kit, {})
        if newtier != "none" and newtier in kit_tier_roles:
            new_tier_role = interaction.guild.get_role(kit_tier_roles[newtier])
            if new_tier_role:
                await member.add_roles(new_tier_role, reason="New tier role added by /results command")

        await bot.get_channel(channels["results"]).send(content=f"<@{user.id}>" ,embed=embed)
        await interaction.followup.send(content=messages["resultMessageSent"], ephemeral=True)
    except Exception as e:
        logging.exception("Error in /results command:")
        await interaction.followup.send(content=messages["error"], ephemeral=True)

@bot.slash_command(name="openqueue", description="opens a kit queue")
async def openqueue(
    interaction: nextcord.Interaction,
    kit: str = nextcord.SlashOption(
        description="Enter kit",
        required=True,
        choices=listKitsText,
    ),
):
    try:
        await interaction.response.defer(ephemeral=True)
        if testerRole not in [role.id for role in interaction.user.roles]:
            await interaction.followup.send(
                messages["noPermission"], ephemeral=True
            )
            return

        response = queue.addTester(kit=kit, userID=interaction.user.id)

        if response[1] == "":
            await interaction.followup.send(
                content=response[0], ephemeral=True
            )
            return

        queue_data = queue.getqueueraw()[kit]
        queue_channel = bot.get_channel(queue_data["queueChannel"])

        if queue_channel is None:
            raise RuntimeError(f"Queue channel for kit '{kit}' was not found.")

        await update_queue_message(
            kit,
            response[1],
            EnterQueueButton(queue, refresh_queue_message),
        )

        await interaction.followup.send(
            content=response[0], ephemeral=True
        )

    except Exception:
        logging.exception("Error in /openqueue command:")
        await interaction.followup.send(
            content=messages["error"], ephemeral=True
        )

@bot.slash_command(name="closequeue", description="closes a kit queue")
async def closequeue(
    interaction: nextcord.Interaction,
    kit: str = nextcord.SlashOption(
        description="Enter kit",
        required=True,
        choices=listKitsText,
    ),
):
    try:
        await interaction.response.defer(ephemeral=True)
        if testerRole not in [role.id for role in interaction.user.roles]:
            await interaction.followup.send(
                messages["noPermission"], ephemeral=True
            )
            return

        response = queue.removeTester(
            userID=interaction.user.id,
            kit=kit,
        )

        if response == "Testing is closed":
            await interaction.followup.send(
                content=response, ephemeral=True
            )
            return

        message_text, embed_data, channel_id, message_id = response
        queue_channel = bot.get_channel(channel_id)

        if queue_channel is None:
            raise RuntimeError(f"Queue channel for kit '{kit}' was not found.")

        await update_queue_message(
            kit,
            embed_data,
            None if message_text == "testing has closed" else EnterQueueButton(queue, refresh_queue_message),
        )

        await interaction.followup.send(
            content=message_text, ephemeral=True
        )

    except Exception:
        logging.exception("Error in /closequeue command:")
        await interaction.followup.send(
            content=messages["error"], ephemeral=True
        )

@bot.slash_command(name="next", description="gets the next user in a kit queue")
async def next(
    interaction: nextcord.Interaction,
    kit: str = nextcord.SlashOption(
        description="Enter kit",
        required=True,
        choices=listKitsText,
    ),
):
    try:
        await interaction.response.defer(ephemeral=True)
        if testerRole not in [role.id for role in interaction.user.roles]:
            await interaction.followup.send(
                messages["noPermission"], ephemeral=True
            )
            return

        queue_data = queue.getqueueraw()[kit]

        if interaction.user.id not in queue_data["testers"]:
            await interaction.followup.send(
                "You are not testing this queue.", ephemeral=True
            )
            return

        user_result = queue.getNextTest(
            testerID=interaction.user.id,
            kit=kit,
        )

        if user_result[0] is None:
            await interaction.followup.send(
                content=user_result[1], ephemeral=True
            )
            return

        user = await interaction.guild.fetch_member(user_result[0])
        user_data = await databaseManager.getUserTicket(user.id, kit)
        if user_data is None:
            await interaction.followup.send(
                f"That user is not registered for the {kit} waitlist.", ephemeral=True
            )
            return
        region = user_data[5]

        category_id = int(
            listKits[kit].get("ticket_category", 0)
            or listRegions[region]["ticket_catagory"]
        )
        category = interaction.guild.get_channel(category_id)
        if category is None:
            raise RuntimeError(f"Ticket category {category_id} was not found.")

        channel = await interaction.guild.create_text_channel(
            name=f"eval-{region}-{kit}-{user.name}",
            category=category,
        )

        await channel.set_permissions(
            user,
            overwrite=nextcord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
            ),
        )

        ticket_message = format.formatticketmessage(
            username=user_data[0],
            tier=user_data[1],
            server=user_data[2],
            kit=user_data[4],
            uuid=user_data[3],
        )

        await channel.send(
            content=f"<@{user.id}>",
            embed=nextcord.Embed.from_dict(ticket_message),
        )

        await interaction.followup.send(
            f"Ticket has been created: <#{channel.id}>",
            ephemeral=True,
        )

    except Exception:
        logging.exception("Error in /next command:")
        await interaction.followup.send(
            content=messages["error"], ephemeral=True
        )

@bot.slash_command(name="closetest", description="closes the current test")
async def closetest(
    interaction: nextcord.Interaction,
    ):
    try:
        if testerRole not in [role.id for role in interaction.user.roles]: await interaction.response.send_message(messages["noPermission"], ephemeral=True); return
        if interaction.channel.category is None or interaction.channel.category.id not in listRegionCategories or interaction.channel.id in listQueueChannel: await interaction.response.send_message(content="You cannot use this command in this channel", ephemeral=True); return
        
        view = CloseTicketButton()

        await interaction.response.send_message("Ticket will be closed in 10 seconds", view=view)
        await asyncio.sleep(10)
        if view.cancelled == False:
            await interaction.channel.delete(reason="Ticket channel closed by command.")
    except Exception as e:
        logging.exception("Error in /closetest command:")
        await interaction.response.send_message(content=messages["error"], ephemeral=True)

@bot.slash_command(name="forceclosetest", description="closes the current test with force")
async def forceclosetest(
    interaction: nextcord.Interaction,
    ):
    try:
        if testerRole not in [role.id for role in interaction.user.roles]: await interaction.response.send_message(messages["noPermission"], ephemeral=True); return
        if interaction.channel.category is None or interaction.channel.category.id not in listRegionCategories or interaction.channel.id in listQueueChannel: await interaction.response.send_message(content="You cannot use this command in this channel", ephemeral=True); return

        await interaction.response.send_message("Ticket will be closed in 10 seconds, cannot cancel")
        await asyncio.sleep(10)
        await interaction.channel.delete(reason="Ticket channel closed by command.")
    except Exception as e:
        logging.exception("Error in /forceclosetest command:")
        await interaction.response.send_message(content=messages["error"], ephemeral=True)

@bot.slash_command(name="updateusername", description="changes a username of a user")
async def updateusername(
    interaction: nextcord.Interaction,
    user: nextcord.User = nextcord.SlashOption(
        description="Enter their discord account",
        required=True,
    ),
    username: str = nextcord.SlashOption(
        description="Enter their minecraft username",
        required=True,
    ),
    kit: str = nextcord.SlashOption(
        description="Choose the kit to update",
        required=True,
        choices=listKitsText,
    )
    ):
    try:
        if testerRole not in [role.id for role in interaction.user.roles]: await interaction.response.send_message(content=messages["noPermission"], ephemeral=True); return
        exists = await databaseManager.userExists(user.id)
        if not exists: await interaction.response.send_message("User does not exist in the database", ephemeral=True); return

        uuid = await mojang.getuserid(username=username)
        if uuid == "8667ba71b85a4004af54457a9734eed7": await interaction.response.send_message(content="Minecraft user does not exist"); return
        await databaseManager.updateUsername(discordID=user.id, kit=kit, username=username, uuid=uuid)
        await interaction.response.send_message(content="Username sucessfully updated", ephemeral=True)
    except Exception as e:
        logging.exception("Error in /updateusername command:")
        await interaction.response.send_message(content=messages["error"], ephemeral=True)


@bot.slash_command(name="updatetier", description="changes a tier of a user in database")
async def updatetier(
    interaction: nextcord.Interaction,
    user: nextcord.User = nextcord.SlashOption(
        description="Enter their discord account",
        required=True,
    ),
    tier: str = nextcord.SlashOption(
        description="Enter their tier",
        required=True,
        choices=listTiers
    ),
    kit: str = nextcord.SlashOption(
        description="Choose the kit to update",
        required=True,
        choices=listKitsText,
    )
    ):
    try:
        if testerRole not in [role.id for role in interaction.user.roles]: await interaction.response.send_message(content=messages["noPermission"], ephemeral=True); return
        exists = await databaseManager.userExists(user.id)
        if not exists: await interaction.response.send_message("User does not exist in the database", ephemeral=True); return

        await databaseManager.updateTier(discordID=user.id, kit=kit, tier=tier)
        await interaction.response.send_message(content="Tier sucessfully updated in database, you will need to change their roles", ephemeral=True)
    except Exception as e: 
        logging.exception("Error in /updatetier command:")
        await interaction.response.send_message(content=messages["error"], ephemeral=True)

@bot.slash_command(name="restrict", description="restrict a user")
async def restrict(
    interaction: nextcord.Interaction,
    user: nextcord.User = nextcord.SlashOption(
        description="Enter their discord account",
        required=True,
    )
    ):
    try:
        if testerRole not in [role.id for role in interaction.user.roles]: await interaction.response.send_message(content=messages["noPermission"], ephemeral=True); return
        exists = await databaseManager.userExists(user.id)
        if not exists: await interaction.response.send_message("User does not exist in the database", ephemeral=True); return

        await databaseManager.updateRestriction(discordID=user.id, restricted=True)

        await interaction.response.send_message(content="User has been restricted", ephemeral=True)
    except Exception as e: 
        logging.exception("Error in /restrict command:")
        await interaction.response.send_message(content=messages["error"], ephemeral=True)

@bot.slash_command(name="unrestrict", description="unrestrict a user")
async def unrestrict(
    interaction: nextcord.Interaction,
    user: nextcord.User = nextcord.SlashOption(
        description="Enter their discord account",
        required=True,
    )
    ):
    try:
        if testerRole not in [role.id for role in interaction.user.roles]: await interaction.response.send_message(content=messages["noPermission"], ephemeral=True); return
        exists = await databaseManager.userExists(user.id)
        if not exists: await interaction.response.send_message("User does not exist in the database", ephemeral=True); return

        await databaseManager.updateRestriction(discordID=user.id, restricted=False)

        await interaction.response.send_message(content="User has been unrestricted", ephemeral=True)
    except Exception as e: 
        logging.exception("Error in /unrestrict command:")
        await interaction.response.send_message(content=messages["error"], ephemeral=True)

@bot.slash_command(name="info", description="gathers info on a user")
async def unrestrict(
    interaction: nextcord.Interaction,
    user: nextcord.User = nextcord.SlashOption(
        description="Enter their discord account",
        required=True,
    )
    ):
    try:
        exists = await databaseManager.userExists(user.id)
        if not exists: await interaction.response.send_message("User does not exist in the database", ephemeral=True); return

        result = await databaseManager.getUserInfo(user.id)
        username, tier, lastTest, region, restricted, uuid, kit = result

        await interaction.response.send_message(embed=nextcord.Embed.from_dict(format.formatinfo(discordName=str(user.name), username=username, tier=tier, lastTest=lastTest, region=region, kit=kit, restricted=restricted, uuid=uuid)))
    except Exception as e: 
        logging.exception("Error in /info command:")
        await interaction.response.send_message(content=messages["error"], ephemeral=True)

@bot.slash_command(name="add", description="adds a user to the ticket")
async def add(
    interaction: nextcord.Interaction,
    user: nextcord.User = nextcord.SlashOption(
        description="Enter their discord account",
        required=True,
    )
    ):
    try:
        if testerRole not in [role.id for role in interaction.user.roles]: await interaction.response.send_message(content=messages["noPermission"], ephemeral=True); return
        if interaction.channel.category is None or interaction.channel.category.id not in listRegionCategories: await interaction.response.send_message(messages["notTicketCatagory"], ephemeral=True); return

        channel = interaction.channel
        overwrite = nextcord.PermissionOverwrite()
        overwrite.view_channel = True
        overwrite.send_messages = True
        await channel.set_permissions(user, overwrite=overwrite)
        await interaction.response.send_message(content=f"<@{user.id}> has been added to the ticket!")

    except Exception as e: 
        logging.exception("Error in /add command:")
        await interaction.response.send_message(content=messages["error"], ephemeral=True)

@bot.slash_command(name="remove", description="removes a user from a ticket")
async def remove(
    interaction: nextcord.Interaction,
    user: nextcord.User = nextcord.SlashOption(
        description="Enter their discord account",
        required=True,
    )
    ):
    try:
        if testerRole not in [role.id for role in interaction.user.roles]: await interaction.response.send_message(content=messages["noPermission"], ephemeral=True); return
        if interaction.channel.category is None or interaction.channel.category.id not in listRegionCategories: await interaction.response.send_message(messages["notTicketCatagory"], ephemeral=True); return
        
        channel = interaction.channel
        overwrite = nextcord.PermissionOverwrite()
        overwrite.view_channel = False
        overwrite.send_messages = False
        await channel.set_permissions(user, overwrite=overwrite)
        await interaction.response.send_message(content=f"<@{user.id}> has been removed from the ticket!")

    except Exception as e: 
        logging.exception("Error in /remove command:")
        await interaction.response.send_message(content=messages["error"], ephemeral=True)

@bot.slash_command(name="passeval", description="passes eval")
async def passeval(
    interaction: nextcord.Interaction,
    user: nextcord.User = nextcord.SlashOption(
    description="Enter their discord account",
    required=True,
    )
    ):
    try:
        if testerRole not in [role.id for role in interaction.user.roles]: await interaction.response.send_message(content=messages["noPermission"], ephemeral=True); return
        if interaction.channel.category is None or interaction.channel.category.id not in listRegionCategories or interaction.channel.id in listQueueChannel: await interaction.response.send_message(content="You cannot use this command in this channel", ephemeral=True); return
        
        channel = interaction.channel
        await channel.edit(name=f"passeval-{user.name}")
        await interaction.response.send_message(content=f"<@{user.id}> has passed eval!")

    except Exception as e: 
        logging.exception("Error in /passeval command:")
        await interaction.response.send_message(content=messages["error"], ephemeral=True)

if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))