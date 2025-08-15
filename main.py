import discord
from discord.ext import commands
import json
import os
import uuid

# Load environment variables for the bot token
try:
    BOT_TOKEN = os.environ['BOT_TOKEN']
    # You still need to replace this with your actual role ID.
    REPORT_ROLE_ID = 123456789012345678
except KeyError:
    print("Error: 'BOT_TOKEN' environment variable not found. Please set it in Railway.")
    exit()

# File to store report log channel IDs
REPORTS_FILE = 'report_logs.json'

def load_data():
    """Loads the report log channel IDs from a JSON file."""
    if os.path.exists(REPORTS_FILE):
        with open(REPORTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    """Saves the report log channel IDs to a JSON file."""
    with open(REPORTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Load data on bot startup
guild_report_logs = load_data()

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Views and Modals for Reporting ---

class ReportPanel(discord.ui.Modal, title="New Report"):
    """Modal to collect all report information at once."""
    reported_discord_id = discord.ui.TextInput(
        label="Reported Discord ID",
        placeholder="e.g., 1234567890",
        required=True
    )
    reason = discord.ui.TextInput(
        label="Reason for Report",
        style=discord.TextStyle.long,
        placeholder="e.g., Harassment, Rule Violation, etc.",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Processes the modal submission and logs the report."""
        await interaction.response.send_message("Report submission acknowledged. Logging report...", ephemeral=True)
        
        report_id = str(uuid.uuid4()).split('-')[0]
        
        embed = discord.Embed(
            title=f"NEW REPORT | ID: {report_id}",
            description="""This log details a report filed through the bot.""",
            color=discord.Color.blue()
        )
        embed.add_field(name="REPORTER", value=f"<@{interaction.user.id}>", inline=True)
        embed.add_field(name="REPORTED USER ID", value=f"<@{self.reported_discord_id.value}>", inline=True)
        embed.add_field(name="REASON", value=self.reason.value, inline=False)
        embed.set_footer(text=f"Logged by {interaction.guild.name} | Seer Bot")
        
        # Log the embed to all registered report channels
        logged_to_count = 0
        for guild_id, channel_id in guild_report_logs.items():
            try:
                guild = bot.get_guild(int(guild_id))
                if guild:
                    channel = guild.get_channel(int(channel_id))
                    if channel:
                        await channel.send(embed=embed)
                        logged_to_count += 1
            except Exception as e:
                print(f"Failed to log report to guild {guild_id}: {e}")
        
        await interaction.followup.send(f"Report has been logged to {logged_to_count} server(s).", ephemeral=True)

# --- Bot Events ---

@bot.event
async def on_ready():
    """Event that fires when the bot is ready and connected to Discord."""
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    await bot.change_presence(activity=discord.Game(name="Scanning the battlefield..."))
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# --- Slash Commands ---

@bot.tree.command(name="new", description="Opens a panel to create a new report.")
async def new_report(interaction: discord.Interaction):
    """
    Command to open the report panel.
    Only users with a specific role can use this command.
    """
    required_role = discord.utils.get(interaction.guild.roles, id=REPORT_ROLE_ID)
    if required_role and required_role in interaction.user.roles:
        await interaction.response.send_modal(ReportPanel())
    else:
        await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)

@bot.tree.command(name="setreportlog", description="Sets the channel where reports will be logged. (Admin only)")
@commands.has_permissions(administrator=True)
async def set_report_log(interaction: discord.Interaction, channel: discord.TextChannel):
    """
    Sets the report log channel for a guild.
    Requires administrator permissions.
    """
    guild_id = str(interaction.guild_id)
    channel_id = str(channel.id)

    guild_report_logs[guild_id] = channel_id
    save_data(guild_report_logs)
    await interaction.response.send_message(f"Successfully set {channel.mention} as the report log channel.", ephemeral=True)

@bot.tree.command(name="removereportlog", description="Removes the report log channel for this server. (Admin only)")
@commands.has_permissions(administrator=True)
async def remove_report_log(interaction: discord.Interaction):
    """
    Removes the report log channel for a guild.
    Requires administrator permissions.
    """
    guild_id = str(interaction.guild_id)
    if guild_id in guild_report_logs:
        del guild_report_logs[guild_id]
        save_data(guild_report_logs)
        await interaction.response.send_message("Successfully removed the report log channel for this server.", ephemeral=True)
    else:
        await interaction.response.send_message("No report log channel is currently set for this server.", ephemeral=True)

# --- Error Handling ---

@bot.event
async def on_command_error(ctx, error):
    """Handles errors from commands."""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have the required permissions to use this command.")

# Run the bot
bot.run(BOT_TOKEN)
