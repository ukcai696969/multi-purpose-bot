from nextcord.ext import commands
import nextcord
import aiosqlite

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
@commands.has_permissions(manage_channels=True)
async def lock(ctx, channel : nextcord.TextChannel=None):
    channel = channel or ctx.channel
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send('Channel locked.')

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx, channel : nextcord.TextChannel=None):
    channel = channel or ctx.channel
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = True
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send('Channel unlocked.')

    
bot.run("token")