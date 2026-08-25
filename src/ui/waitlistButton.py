import datetime
import nextcord
from nextcord import ui

from src.database import databaseManager
from src.utils.mojang import getuserid
from src.utils.loadConfig import (
    messages, listRegions, listHighTiers, catagories, listKits, branding, cooldown
)
from src.utils import format

class WaitlistButton(ui.View):
    """Eight kit buttons. Each button opens a form with that kit pre-selected."""

    def __init__(self):
        super().__init__(timeout=None)
        for kit, kit_data in listKits.items():
            button = ui.Button(
                label=kit_data.get("label", kit.title()),
                style=nextcord.ButtonStyle.primary,
                custom_id=f"waitlist:kit:{kit}",
                row=None,
            )
            emoji_id = int(kit_data.get("emoji_id", 0) or 0)
            if emoji_id:
                button.emoji = nextcord.PartialEmoji(name=kit, id=emoji_id)
            button.callback = self._make_callback(kit)
            self.add_item(button)

    def _make_callback(self, kit):
        async def callback(interaction: nextcord.Interaction):
            exists = await databaseManager.userExists(interaction.user.id)
            if exists:
                if await databaseManager.isRestriced(interaction.user.id):
                    await interaction.response.send_message("You are currently restricted.", ephemeral=True)
                    return

                lastTest = (await databaseManager.getLastTest(interaction.user.id))[0]
                if int(datetime.datetime.now().timestamp()) - lastTest <= int(
                    __import__("src.utils.loadConfig", fromlist=["cooldown"]).cooldown
                ) * 60:
                    await interaction.response.send_message(
                        f"You can test again at: <t:{lastTest + (int(cooldown) * 60)}:f>",
                        ephemeral=True
                    )
                    return

                current_tier = (await databaseManager.getTier(interaction.user.id))[0]
                if current_tier in listHighTiers:
                    categoryChannel = interaction.guild.get_channel(catagories["highTests"])
                    channelID = await interaction.guild.create_text_channel(
                        name=f"highTest-{interaction.user.name}",
                        category=categoryChannel
                    )
                    overwrite = nextcord.PermissionOverwrite(view_channel=True, send_messages=True)
                    await channelID.set_permissions(interaction.user, overwrite=overwrite)
                    messageData = await databaseManager.getUserTicket(interaction.user.id)
                    ticketMessage = format.formathighticketmessage(
                        username=messageData[0], tier=messageData[1],
                        kit=messageData[4], uuid=messageData[3]
                    )
                    await channelID.send(content=f"<@{interaction.user.id}>", embed=nextcord.Embed.from_dict(ticketMessage))
                    await interaction.response.send_message(
                        content=f"A high tier ticket has been created: <#{channelID.id}>",
                        ephemeral=True
                    )
                    return

            await interaction.response.send_modal(WaitlistForm(kit))
        return callback


class WaitlistForm(ui.Modal):
    def __init__(self, kit):
        super().__init__(f"Join {listKits[kit].get('label', kit.title())} Waitlist")
        self.kit = kit

        self.ign = ui.TextInput(
            label="Minecraft Username",
            placeholder="Enter your in-game name",
            required=True
        )
        self.region = ui.TextInput(
            label=f"Region ({', '.join(listRegions.keys())})",
            placeholder="EU or NA",
            required=True
        )
        self.server = ui.TextInput(
            label="Preferred Server",
            placeholder="Enter your preferred server",
            required=True
        )
        self.add_item(self.ign)
        self.add_item(self.region)
        self.add_item(self.server)

    async def callback(self, interaction: nextcord.Interaction):
        try:
            uuid = await getuserid(self.ign.value.strip())
            if uuid == "8667ba71b85a4004af54457a9734eed7":
                await interaction.response.send_message("Minecraft username does not exist.", ephemeral=True)
                return

            region_lookup = {name.lower(): name for name in listRegions}
            region = region_lookup.get(self.region.value.strip().lower())
            if region is None:
                await interaction.response.send_message(
                    f"Invalid region. Choose one of: {', '.join(listRegions)}",
                    ephemeral=True
                )
                return

            await databaseManager.addUser(
                discordID=interaction.user.id,
                minecraftUsername=self.ign.value.strip(),
                minecraftUUID=uuid,
                tier="none",
                lastTest=0,
                server=self.server.value.strip(),
                region=region,
                kit=self.kit
            )

            current_roles = interaction.user.roles
            region_role_ids = [r["role_ping"] for r in listRegions.values()]
            role_ids_to_remove = [role.id for role in current_roles if role.id in region_role_ids]
            if role_ids_to_remove:
                await interaction.user.remove_roles(
                    *[interaction.guild.get_role(role_id) for role_id in role_ids_to_remove if interaction.guild.get_role(role_id)]
                )

            role = interaction.guild.get_role(listRegions[region]["role_ping"])
            if role is None:
                await interaction.response.send_message(
                    "Bot is not configured correctly: region role not found.",
                    ephemeral=True
                )
                return
            await interaction.user.add_roles(role)

            queue_key = self.kit
            await interaction.response.send_message(
                f"You are registered for **{listKits[self.kit].get('label', self.kit.title())}** in **{region}**. "
                f"Queue: `{queue_key}` • <#{listKits[self.kit]['queue_channel']}>",
                ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(messages["error"], ephemeral=True)
