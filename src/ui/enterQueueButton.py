import nextcord
from nextcord import ui

from src.utils.loadConfig import messages
from src.tierlistQueue import TierlistQueue
from src.database import databaseManager

class EnterQueueButton(ui.View):
    def __init__(self, queue):
        super().__init__(timeout=None)
        self.queue: TierlistQueue = queue

    @nextcord.ui.button(label="Enter Queue", style=nextcord.ButtonStyle.primary, custom_id="joinQueue")
    async def enter_queue(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        try:
            if await databaseManager.userExists(interaction.user.id):
                if await databaseManager.isRestriced(interaction.user.id):
                    await interaction.response.send_message("You are currently restricted.", ephemeral=True)
                    return
            else:
                await interaction.response.send_message(
                    "Please enter your details in the waitlist panel first.",
                    ephemeral=True
                )
                return

            response = self.queue.addUser(interaction.message.id, interaction.user.id)
            await interaction.response.send_message(content=response, ephemeral=True)
        except Exception:
            await interaction.response.send_message(messages["error"], ephemeral=True)

    @nextcord.ui.button(label="Exit Queue", style=nextcord.ButtonStyle.danger, custom_id="leaveQueue")
    async def exit_queue(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        try:
            response = self.queue.removeUser(interaction.message.id, interaction.user.id)
            await interaction.response.send_message(content=response, ephemeral=True)
        except Exception:
            await interaction.response.send_message(messages["error"], ephemeral=True)
