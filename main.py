import discord
from discord.ext import commands
import aiosqlite
import easy_pil
from easy_pil import *
import asyncio
import os
import random

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("Bot is ready")
    setattr(bot, "db", await aiosqlite.connect("level.db"))
    await asyncio.sleep(3)
    async with bot.db.cursor() as cursor:
        await cursor.execute("CREATE TABLE IF NOT EXISTS levels (level INTEGER, xp INTEGER, user INTEGER, guild INTEGER)")
        await cursor.execute("CREATE TABLE IF NOT EXISTS levelSettings (levelsys BOOL, role INTEGER, levelreq INTEGER, guild INTEGER)")
        await bot.db.commit()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    author = message.author
    guild = message.guild
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT levelsys FROM levelSettings WHERE guild = ?", (guild.id,))
        levelsys = await cursor.fetchone()
        if levelsys and not levelsys[0]:
            return
        await cursor.execute("SELECT xp FROM levels WHERE user = ? AND guild = ?", (author.id, guild.id,))
        xp = await cursor.fetchone()
        await cursor.execute("SELECT level FROM levels WHERE user = ? AND guild = ?", (author.id, guild.id,))
        level = await cursor.fetchone()

        if not xp or not level:
            await cursor.execute("INSERT INTO levels (level, xp, user, guild) VALUES (?, ?, ?, ?)", (0, 0, author.id, guild.id,))
            await bot.db.commit()
            return
        
        try:
            xp = xp[0]
            level = level[0]
        except TypeError:
            xp = 0
            level = 0
        
        if level < 5:
            xp += random.randint(10, 15)
            await cursor.execute("UPDATE levels SET xp = ? WHERE user = ? AND guild = ?", (xp, author.id, guild.id,))
        else:
            rand = random.randint(1, (level//4))
            if rand == 1:
                xp += random.randint(10, 15)
                await cursor.execute("UPDATE levels SET xp = ? WHERE user = ? AND guild = ?", (xp, author.id, guild.id,)) 
        if xp >= 100:
            level += 1
            await cursor.execute("UPDATE levels SET level = ? WHERE user = ? AND guild = ?", (level, author.id, guild.id,))
            await cursor.execute("UPDATE levels SET xp = ? WHERE user = ? AND guild = ?", (0, author.id, guild.id,))
            await message.channel.send(f"{author.mention} has leveled up to level {level}")

        await bot.db.commit()
        await bot.process_commands(message)

@bot.command()
async def level(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author
    async with bot.db.cursor() as cursor:
        await cursor.exexute("SELECT levelsys FROM levelSettings WHERE guild = ?", (ctx.guild.id,))
        levelsys = await cursor.fetchone()
        if levelsys and not levelsys[0]:
            return 
        await cursor.execute("SELECT xp FROM levels WHERE user = ? AND guild = ?", (member.id, ctx.guild.id,))
        xp = await cursor.fetchone()
        await cursor.execute("SELECT level FROM levels WHERE user = ? AND guild = ?", (member.id, ctx.guild.id,))
        level = await cursor.fetchone()
        if not xp or not level:
            await cursor.execute("INSERT INTO levels (level, xp, user, guild) VALUES (?, ?, ?, ?)", (0, 0, member.id, ctx.guild.id,))

        try:
            xp = xp[0]
            level = level[0]
        except TypeError:
            xp = 0
            level = 0
        
        user_data = {
            "name": f"{member.name}#{member.discriminator}",
            "xp": xp, 
            "level": level,
            "next_level": 100,
            "percentage": xp,
        }
    
        background = Editor(Canvas((900, 300), color="#141414"))
        profile_picture = await load_image_async(str(member.avatar.url))
        profile = Editor(profile_picture).resize((150, 150)).circle_image()

        popins = Font.poppins(size=40)
        popins_small = Font.poppins(size=30)

        card_right_shape = [(600, 0), (750, 300), (900, 300), (900, 0)]

        background.polygon(card_right_shape, color="#FFFFFF")
        background.paste(profile, (30, 30))

        background.rectangle((30, 220), width=650, height=40, color="#FFFFFF")
        background.bar((30, 220), max_width=650, height=40, percentage=user_data["percentage"], color="#FFFFFF", radius=20)
        background.text((200, 40), user_data["name"], font=popins, color="#FFFFFF")

        background.rectangle((200, 100), width=350, height=2, fill="#FFFFFF")
        background.text(
            (200, 120),
            f"Level - {user_data['level']} | XP - {user_data['xp']}/{user_data['next_level']}",
            font=popins_small,
            color="#FFFFFF"
        )

        file = discord.File(fp=background.image_bytes, filename="level.png")
        await ctx.send(file=file)

@bot.group()
async def slvl(ctx):
    return
    
@slvl.command(alias=["e"])
@commands.has_guild_permissions(manage_guild=True)
async def enable(ctx):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT levelsys FROM levelSettings WHERE guild = ?", (ctx.guild.id,))
        levelsys = await cursor.fetchone()
        if levelsys:
            if levelsys[0]:
                return await ctx.send("Leveling system is already enabled")
            await cursor.execute("UPDATE levelSettings SET levelsys = ? WHERE guild = ?", (True, ctx.guild.id,))
        else:
            await cursor.execute("INSERT INTO levelSettings VALUES (?, ?, ?, ?)", (True, 0, 0, ctx.guild.id,))
        await ctx.send("Leveling system enabled")
    await bot.db.commit()

@slvl.command(alias=["d"])
@commands.has_guild_permissions(manage_guild=True)
async def disable(ctx):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT levelsys FROM levelSettings WHERE guild = ?", (ctx.guild.id,))
        levelsys = await cursor.fetchone()
        if levelsys:
            if not levelsys[0]:
                return await ctx.send("Leveling system is already diabled")
            await cursor.execute("UPDATE levelSettings SET levelsys = ? WHERE guild = ?", (False, ctx.guild.id,))
        else:
            await cursor.execute("INSERT INTO levelSettings VALUES (?, ?, ?, ?)", (False, 0, 0, ctx.guild.id,))
        await ctx.send("Leveling system disabled")
    await bot.db.commit()
    



bot.run("token here")