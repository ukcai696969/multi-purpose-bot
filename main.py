from nextcord.ext import commands
import nextcord
import aiosqlite
import asyncio
import random
import time
import multiprocessing
import datetime
import psutil

class AddUser(nextcord.ui.Modal):
    def __init__(self, channel):
        super().__init__(
            "Add User",
            timeout=300,
        )
        self.channel = channel

        self.user = nextcord.ui.TextInput(
            label="User ID",
            min_length=2,
            max_length=32,
            required=True,
            placeholder="User ID(MUST BE INT)"
        )

        self.add_item(self.user)
    
    async def callback(self, interaction: nextcord.Interaction) -> None:
        user = interaction.guild.get_member(int(self.user.value))
        if user is None:
            return await interaction.response.send_message(f"Invaild User ID", ephemeral=True)
        overwirte = nextcord.PermissionOverwrite()
        overwirte.read_messages = True
        await self.channel.set_permissions(user, overwrite=overwirte)
        await interaction.response.send_message(f"Added {user.mention} to {self.channel.mention}", ephemeral=True)



class RemoveUser(nextcord.ui.Modal):
    def __init__(self, channel):
        super().__init__(
            "Remove User",
            timeout=300,
        )
        self.channel = channel

        self.user = nextcord.ui.TextInput(
            label="User ID",
            min_length=2,
            max_length=32,
            required=True,
            placeholder="User ID(MUST BE INT)"
        )

        self.add_item(self.user)
    
    async def callback(self, interaction: nextcord.Interaction) -> None:
        user = interaction.guild.get_member(int(self.user.value))
        if user is None:
            return await interaction.response.send_message(f"Invaild User ID", ephemeral=True)
        overwirte = nextcord.PermissionOverwrite()
        overwirte.read_messages = False
        await self.channel.set_permissions(user, overwrite=overwirte)
        await interaction.response.send_message(f"Removed {user.mention} to {self.channel.mention}", ephemeral=True)





class CreateTicket(nextcord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    @nextcord.ui.button(label="Create Ticket", style=nextcord.ButtonStyle.green, custom_id="create_ticket")
    async def create_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        msg = await interaction.response.send_message("Ticket is being created...", ephemeral=True)
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT role FROM roles WHERE guild = ?", (interaction.guild.id,))
            role = await cursor.fetchone()
            if role:
                overwrites = {
                    interaction.guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
                    interaction.guild.me: nextcord.PermissionOverwrite(read_messages=True),
                    interaction.guild.get_role(role[0]): nextcord.PermissionOverwrite(read_messages=True)
             }

            else:
                overwrites = {
                    interaction.guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
                    interaction.guild.me: nextcord.PermissionOverwrite(read_messages=True)
                }



        channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
        await msg.edit(content=f"Ticket created! {channel.mention}")
        embed = nextcord.Embed(title="Ticket Created", description=f"Ticket created by {interaction.user.mention}", color=nextcord.Color.green())
        await channel.send(embed=embed, view=TicketSettings())


class TicketSettings(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="Close Ticket", style=nextcord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message("Ticket is being closed...", ephemeral=True)
        await interaction.channel.delete()
        await interaction.user.send(f"Ticket in {interaction.guild.name} has been closed. By {interaction.user.mention}")
    
    @nextcord.ui.button(label="Add User", style=nextcord.ButtonStyle.blurple, custom_id="add_user")
    async def add_user(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(AddUser(interaction.channel))

    @nextcord.ui.button(label="Remove User", style=nextcord.ButtonStyle.blurple, custom_id="remove_user")
    async def remove_user(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(RemoveUser(interaction.channel))


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persistent_views_added = False

    async def on_ready(self):
        if not self.persistent_views_added:
            self.add_view(CreateTicket(self))
            self.add_view(TicketSettings())
            self.persistent_views_added = True
            print("Persistent views added")
            self.db = await aiosqlite.connect("tickets.db")
            async with self.db.cursor() as cursor:
                await cursor.execute("CREATE TABLE IF NOT EXISTS roles (role INTEGER, guild INTEGER)")
            print("Database connected")

        print(f"Logged in as {self.user}")
        print("Ready!")


intents = nextcord.Intents.all()
bot = Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    em = nextcord.Embed(title="Ticket", description="Click the button to create a ticket")
    await ctx.send(embed=em, view=CreateTicket(bot))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_role(ctx, role: nextcord.Role):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT role FROM roles WHERE guild = ?", (ctx.guild.id,))
        role2 = await cursor.fetchone()
        if role2:
            await cursor.execute("UPDATE roles SET role = ? WHERE guild = ?", (role.id, ctx.guild.id))
            await ctx.send(f"Tickets Auto-Assign Role has been updated to {role.mention}")
        else:
            await cursor.execute("INSERT INTO roles VALUES (?, ?)", (role.id, ctx.guild.id,))
            await ctx.send(f"Tickets Auto-Assign Role Added")
        await bot.db.commit()


@bot.command()  
async def serverinfo(ctx):
    role_count = len(ctx.guild.roles)
    emoji_count = len(ctx.guild.emojis)
    list_of_bots = [bot.mention for bot in ctx.guild.members if bot.bot]

    embed = nextcord.Embed(title=f"Server Info - {ctx.guild.name}", description="Server Information", color=nextcord.Color.green())
    embed.add_field(name="Server ID", value=ctx.guild.id, inline=False)
    embed.add_field(name="Server Owner", value=ctx.guild.owner, inline=False)
    embed.add_field(name="Server Region", value=ctx.guild.region, inline=False)
    embed.add_field(name="Verification Level", value=ctx.guild.verification_level, inline=False)
    embed.add_field(name="Total Members", value=ctx.guild.member_count, inline=False)
    embed.add_field(name="Total Bots", value=len(list_of_bots), inline=False)
    embed.add_field(name="Total Text Channels", value=len(ctx.guild.text_channels), inline=False)
    embed.add_field(name="Total Voice Channels", value=len(ctx.guild.voice_channels), inline=False)
    embed.add_field(name="Total Categories", value=len(ctx.guild.categories), inline=False)
    embed.add_field(name="Total Roles", value=role_count, inline=False)
    embed.add_field(name="Total Emojis", value=emoji_count, inline=False)
    embed.add_field(name="Created At", value=ctx.guild.created_at.strftime("%a, %#d %B %Y, %I:%M %p UTC"), inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: nextcord.Member = None):
    if not member:
        member = ctx.author

    roles = [role for role in member.roles]

    embed = nextcord.Embed(colour=member.color, timestamp=ctx.message.created_at)

    embed.set_author(name=f"User Info - {member}")
    embed.set_footer(text=f"Requested by {ctx.author}")

    embed.add_field(name="ID:", value=member.id)
    embed.add_field(name="Guild Name:", value=member.display_name)

    embed.add_field(name="Created Account On:", value=member.created_at.strftime("%a, %#d %B %Y, %I:%M %p UTC"))
    embed.add_field(name="Joined Server On:", value=member.joined_at.strftime("%a, %#d %B %Y, %I:%M %p UTC"))

    embed.add_field(name=f"Roles ({len(roles)})", value=" ".join([role.mention for role in roles]))
    embed.add_field(name="Top Role:", value=member.top_role.mention)

    embed.add_field(name="Bot?", value=member.bot)

    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, member: nextcord.Member = None):
    if not member:
        member = ctx.author

    embed = nextcord.Embed(title=f"{member}'s Avatar", color=nextcord.Color.green())
    embed.set_image(url=member.avatar.url)
    await ctx.send(embed=embed)


@bot.command()
async def help(ctx):
    embed = nextcord.Embed(title="Help", description="Help Command", color=nextcord.Color.green())
    embed.add_field(name="!setup_ticket", value="Sets up a ticket system", inline=False)
    embed.add_field(name="!setup_role", value="Sets up a role for auto-assigning", inline=False)
    embed.add_field(name="!serverinfo", value="Shows server information", inline=False)
    embed.add_field(name="!userinfo", value="Shows user information", inline=False)
    embed.add_field(name="!botinfo", value="Shows bot information", inline=False)
    embed.add_field(name="!avatar", value="Shows user avatar", inline=False)
    embed.add_field(name="!help", value="Shows this message", inline=False)
    embed.add_field(name="Stats", value="Shows bot stats", inline=False)
    embed.add_field(name="!ping", value="Shows bot latency", inline=False)
    embed.add_field(name="!_8ball", value="Ask the bot a question", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_guild_join(guild):
    em = nextcord.Embed(title="Thanks for adding me!", description="Thanks for adding me to your server! To get started, do !setup_ticket to set up a ticket system. If you need help, join the support server: https://discord.gg/4Z3Z7Z9")
    await guild.send(embed=em)

@bot.command()
async def stats(ctx):
    embed = nextcord.Embed(title="Stats", description="Bot Stats", color=nextcord.Color.green())
    embed.add_field(name="Servers", value=len(bot.guilds), inline=False)
    embed.add_field(name="Users", value=len(bot.users), inline=False)
    embed.add_field(name="Channels", value=len(bot.channels), inline=False)
    await ctx.send(embed=embed)

@bot.command(alises=["8b"])
async def _8ball(ctx, question):
    responses = ['As I see it, yes.',
             'Yes.',
             'Positive',
             'From my point of view, yes',
             'Convinced.',
             'Most Likley.',
             'Chances High',
             'No.',
             'Negative.',
             'Not Convinced.',
             'Perhaps.',
             'Not Sure',
             'Mayby',
             'I cannot predict now.',
             'Im to lazy to predict.',
             'I am tired. *proceeds with sleeping*']
    response = random.choice(responses)
    embed=nextcord.Embed(title="The Magic 8 Ball has Spoken!")
    embed.add_field(name='Question: ', value=f'{question}', inline=True)
    embed.add_field(name='Answer: ', value=f'{response}', inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    em = nextcord.Embed(title="Pong!", description=f"{round(bot.latency * 1000)}ms")

@bot.command()
async def botinfo(ctx):
    embed = nextcord.Embed(title="Bot Info", description="Bot Information", color=nextcord.Color.green())
    embed.add_field(name="Bot Name", value=bot.user.name, inline=False)
    embed.add_field(name="Bot ID", value=bot.user.id, inline=False)
    embed.add_field(name="Cpu Cores", value=multiprocessing.cpu_count(), inline=False)
    embed.add_field(name="Bot Latency", value=f"{round(bot.latency * 1000)}ms", inline=False)
    embed.add_field(name="Cpu Usage", value=f"{psutil.cpu_percent()}%", inline=False)
    embed.add_field(name="Memory Usage", value=f"{psutil.virtual_memory().percent}%", inline=False)
    embed.add_field(name="Total Memory", value=f"{round(psutil.virtual_memory().total / (1024.0 **3))} GB", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def rps(ctx, choice):
    choices=["rock", "paper", "scissors"]
    if choice not in choices:
        embed = nextcord.Embed(title="Error", description="Please choose rock, paper or scissors", color=nextcord.Color.red())
        await ctx.send(embed=embed)
    else:
        em = nextcord.Embed(title="Rock Paper Scissors", description=f"{ctx.author.mention} chose {choice} i choose {random.choice(choices)}", color=nextcord.Color.random())
        await ctx.send(embed=em)

