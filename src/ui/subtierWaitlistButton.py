import datetime
import nextcord
from nextcord import ui

from src.database import databaseManager
from src.utils.mojang import getuserid
from src.utils.loadConfig import listRegions, cooldown

class SubtierWaitlistView(ui.View):
    """Persistent select menu for the separately managed sub-tier waitlist."""
    def __init__(self, subtiers):
        super().__init__(timeout=None)
        options = [nextcord.SelectOption(label=name[:100], value=name[:100]) for name in subtiers[:25]]
        if not options:
            options = [nextcord.SelectOption(label="No subtiers available", value="__none__", description="A tester must add a subtier first.")]
        select = ui.Select(
            placeholder="Select a subtier to join its waitlist",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="onyx:subtier:select",
        )
        select.callback = self._callback
        self.add_item(select)

    async def _callback(self, interaction: nextcord.Interaction):
        subtier = interaction.data.get("values", ["__none__"])[0]
        if subtier == "__none__":
            await interaction.response.send_message("There are no subtiers available yet.", ephemeral=True)
            return
        if subtier not in await databaseManager.getSubtiers():
            await interaction.response.send_message("That subtier no longer exists. Please reopen the panel.", ephemeral=True)
            return
        await interaction.response.send_modal(SubtierWaitlistForm(subtier))

class SubtierWaitlistForm(ui.Modal):
    def __init__(self, subtier):
        super().__init__(f"Join {subtier} Subtier Waitlist")
        self.subtier = subtier
        self.ign = ui.TextInput(label="Minecraft Username", required=True, placeholder="Enter your in-game name")
        self.region = ui.TextInput(label=f"Region ({', '.join(listRegions.keys())})", required=True, placeholder="EU or NA")
        self.server = ui.TextInput(label="Preferred Server", required=True, placeholder="Enter your preferred server")
        self.add_item(self.ign); self.add_item(self.region); self.add_item(self.server)

    async def callback(self, interaction: nextcord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            if await databaseManager.isRestriced(interaction.user.id):
                await interaction.followup.send("You are currently restricted.", ephemeral=True); return
            uuid = await getuserid(self.ign.value.strip())
            region_lookup = {name.lower(): name for name in listRegions}
            region = region_lookup.get(self.region.value.strip().lower())
            if region is None:
                await interaction.followup.send(f"Invalid region. Choose one of: {', '.join(listRegions)}", ephemeral=True); return
            existing = await databaseManager.getSubtierUser(interaction.user.id, self.subtier)
            if existing:
                last_test = int(existing[2] or 0)
                if last_test and int(datetime.datetime.now().timestamp()) - last_test <= int(cooldown) * 60:
                    await interaction.followup.send(f"You can test again at: <t:{last_test + int(cooldown)*60}:f>", ephemeral=True); return
            await databaseManager.addSubtierUser(interaction.user.id, self.subtier, self.ign.value.strip(), uuid, existing[2] if existing else 0, self.server.value.strip(), region)
            await interaction.followup.send(f"You are registered for **{self.subtier}**. A tester can now take you from the subtier waitlist.", ephemeral=True)
        except Exception:
            await interaction.followup.send("An error occurred.", ephemeral=True)
