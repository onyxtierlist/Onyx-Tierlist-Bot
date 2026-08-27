import nextcord
from nextcord import ui

from src.utils.loadConfig import messages
from src.tierlistQueue import TierlistQueue
from src.database import databaseManager

class EnterQueueButton(ui.View):
    def __init__(self, queue, refresh_queue=None):
        super().__init__(timeout=None)
        self.queue: TierlistQueue = queue
        self.refresh_queue = refresh_queue

    @nextcord.ui.button(label="Enter Queue", style=nextcord.ButtonStyle.primary, custom_id="joinQueue")
    async def enter_queue(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            queue_kit = self.queue.find_by_message(interaction.message.id)
            if queue_kit is None:
                await interaction.followup.send("This queue is no longer available.", ephemeral=True)
                return
            if not await databaseManager.userExists(interaction.user.id):
                await interaction.followup.send(
                    "Please enter your details in the waitlist panel first.",
                    ephemeral=True
                )
                return
            if await databaseManager.isRestriced(interaction.user.id):
                await interaction.followup.send("You are currently restricted.", ephemeral=True)
                return
            if await databaseManager.getUserTicket(interaction.user.id, queue_kit) is None:
                await interaction.followup.send(
                    f"Please enter your details for the {queue_kit} waitlist first.",
                    ephemeral=True
                )
                return

            response = self.queue.addUser(interaction.message.id, interaction.user.id)
            if self.refresh_queue and response == messages["addToQueue"]:
                await self.refresh_queue(queue_kit)
            await interaction.followup.send(content=response, ephemeral=True)
        except Exception:
            await interaction.followup.send(messages["error"], ephemeral=True)

    @nextcord.ui.button(label="Exit Queue", style=nextcord.ButtonStyle.danger, custom_id="leaveQueue")
    async def exit_queue(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            queue_kit = self.queue.find_by_message(interaction.message.id)
            if queue_kit is None:
                await interaction.followup.send("This queue is no longer available.", ephemeral=True)
                return

            response = self.queue.removeUser(interaction.message.id, interaction.user.id)
            if self.refresh_queue and response == messages["leaveQueue"]:
                await self.refresh_queue(queue_kit)
            await interaction.followup.send(content=response, ephemeral=True)
        except Exception:
            await interaction.followup.send(messages["error"], ephemeral=True)
