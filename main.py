import discord
from discord.ext import commands
import json
import os
import uuid

try:
    BOT_TOKEN = os.environ['BOT_TOKEN']
    REPORT_ROLE_ID = 1405908410032984144
except KeyError:
    print("Error: 'BOT_TOKEN' environment variable not found. Please set it in Railway.")
    exit()

REPORTS_FILE = 'report_logs.json'

def load_data():
    if os.path.exists(REPORTS_FILE):
        with open(REPORTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(REPORTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

guild_report_logs = load_data()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

class ReportPanel(discord.ui.Modal, title="New Report"):
    reporter_info = discord.ui.TextInput(
        label="Reporter Username & ID",
        placeholder="e.g., JaneDoe#1234, 1234567890",
        required=True
    )
    reported_info = discord.ui.TextInput(
        label="Reported User Username & ID",
        placeholder="e.g., JohnDoe#5678, 1234567890",
        required=True
    )
    reason = discord.ui.TextInput(
        label="Reason for Report",
        style=discord.TextStyle.long,
        placeholder="Provide as much detail as possible...",
        required=True
    )
    additional_info = discord.ui.TextInput(
        label="Additional Info (Optional)",
        style=discord.TextStyle.long,
        placeholder="Any other details, proof links, or context.",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Report submission acknowledged. Logging report...", ephemeral=True)
        
        report_id = str(uuid.uuid4()).split('-')[0]
        
        # --- Start of the fix ---
        
        # Robustly split the reporter info, providing a default if no comma is found
        reporter_parts = self.reporter_info.value.split(',', 1)
        if len(reporter_parts) == 2:
            reporter_username, reporter_id = [part.strip() for part in reporter_parts]
        else:
            reporter_username = self.reporter_info.value
            reporter_id = "N/A" # Default value if no ID is provided

        # Robustly split the reported user info
        reported_parts = self.reported_info.value.split(',', 1)
        if len(reported_parts) == 2:
            reported_username, reported_id = [part.strip() for part in reported_parts]
        else:
            reported_username = self.reported_info.value
            reported_id = "N/A" # Default value if no ID is provided
        
        # --- End of the fix ---

        embed = discord.Embed(
            title=f"NEW REPORT | ID: {report_id}",
            description=f"A new report has been filed by `{reporter_username}`.",
            color=discord.Color.blue()
        )
        embed.add_field(name="REPORTER", value=f"**Username:** `{reporter_username}`\n**ID:** {reporter_id}", inline=False)
        embed.add_field(name="REPORTED USER", value=f"**Username:** `{reported_username}`\n**ID:** {reported_id}", inline=False)
        embed.add_field(name="REASON", value=self.reason.value, inline=False)
        if self.additional_info.value:
            embed.add_field(name="ADDITIONAL INFO", value=self.additional_info.value, inline=False)
        embed.set_footer(text=f"Reported from server: {interaction.guild.name} | By seer")
        
        logged_to_count = 0
        for guild_id, channel_id in guild_report_logs.items():
            try:
                guild = bot.get_guild(int(guild_id))
                if not guild:
                    print(f"Guild {guild_id} not found.")
                    continue
                
                channel = guild.get_channel(int(channel_id))
                if not channel:
                    print(f"Channel {channel_id} not found in guild {guild_id}.")
                    continue

                if not channel.permissions_for(guild.me).send_messages:
                    print(f"Bot lacks 'send_messages' permission in channel {channel.name} ({channel.id}) of guild {guild.name}.")
                    continue
                
                await channel.send(embed=embed)
                logged_to_count += 1
            except Exception as e:
                print(f"Failed to log report to guild {guild_id}: {e}")
        
        await interaction.followup.send(f"Report has been logged to {logged_to_count} server(s).", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    await bot.change_presence(activity=discord.Game(name="Scanning the battlefield..."))
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="new", description="Opens a panel to create a new report.")
async def new_report(interaction: discord.Interaction):
    required_role = discord.utils.get(interaction.guild.roles, id=REPORT_ROLE_ID)
    if required_role and required_role in interaction.user.roles:
        await interaction.response.send_modal(ReportPanel())
    else:
        await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)

@bot.tree.command(name="setreportlog", description="Sets the channel where reports will be logged. (Admin only)")
@commands.has_permissions(administrator=True)
async def set_report_log(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild_id)
    channel_id = str(channel.id)

    if not channel.permissions_for(interaction.guild.me).send_messages:
        await interaction.response.send_message(f"I do not have permission to send messages in {channel.mention}. Please grant me the necessary permissions.", ephemeral=True)
        return

    guild_report_logs[guild_id] = channel_id
    save_data(guild_report_logs)
    await interaction.response.send_message(f"Successfully set {channel.mention} as the report log channel.", ephemeral=True)

@bot.tree.command(name="removereportlog", description="Removes the report log channel for this server. (Admin only)")
@commands.has_permissions(administrator=True)
async def remove_report_log(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    if guild_id in guild_report_logs:
        del guild_report_logs[guild_id]
        save_data(guild_report_logs)
        await interaction.response.send_message("Successfully removed the report log channel for this server.", ephemeral=True)
    else:
        await interaction.response.send_message("No report log channel is currently set for this server.", ephemeral=True)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have the required permissions to use this command.")

bot.run(BOT_TOKEN)
