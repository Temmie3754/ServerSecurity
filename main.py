import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
import re
from difflib import get_close_matches
from unidecode import unidecode
import sqlite3
import datetime
import shortuuid as shortuuid
from apiclient import discovery
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pandas as pd
import pickle
import asyncio
from discord.ext.commands import MissingPermissions
from discord.ext import tasks
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_permission
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType
import ast

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
intents.members = True
intents.bans = True
bot = commands.Bot(command_prefix="£", intents=intents)
slash = SlashCommand(bot, sync_commands=True)
userdict = {}
sqlite_file = 'guildsettings.db'
conn = sqlite3.connect(sqlite_file)
c = conn.cursor()


@tasks.loop(hours=1)
async def hourloop():
    for user in userdict:
        if 'delchanneltime' in user:
            if datetime.datetime.utcnow() - user['delchanneltime'].days >= 1:
                del user['delchanneltime']
                del user['delchannel']
        if 'delmembertime' in user:
            if datetime.datetime.utcnow() - user['delmembertime'].days >= 1:
                del user['delmembertime']
                del user['delmember']


guild_ids = []


@bot.event
async def on_ready():
    global guild_ids, imagechannel
    print(f'{bot.user} has connected to Discord!')
    for guild in bot.guilds:
        print(f'Connected to {guild.name}')
        guild_ids.append(guild.id)
    DiscordComponents(bot)
    imagechannel = bot.get_channel(856629294684176415)


@bot.event
async def on_guild_channel_delete(channel):
    async for entry in channel.guild.audit_logs(limit=1):
        if entry.action == discord.AuditLogAction.channel_delete:
            if str(entry.user.id) in userdict:
                if 'delchannel' not in userdict[str(entry.user.id)]:
                    userdict[str(entry.user.id)]['delchannel'] = 0
            else:
                userdict[str(entry.user.id)] = {'delchannel': 0}
            userdict[str(entry.user.id)]['delchannel'] += 1
            userdict[str(entry.user.id)]['delchanneltime'] = datetime.datetime.utcnow()
            c.execute("SELECT * FROM guildsInfo WHERE guildID=?", (channel.guild.id,))
            row = c.fetchone()
            if userdict[str(entry.user.id)]['delchannel'] >= row[2]:
                await entry.user.edit(roles=[])


@bot.event
async def on_member_remove(member):
    print("removed")
    async for entry in member.guild.audit_logs(limit=1):
        if entry.action == discord.AuditLogAction.kick or entry.action == discord.AuditLogAction.ban:
            if str(entry.user.id) in userdict:
                if 'delmember' not in userdict[str(entry.user.id)]:
                    userdict[str(entry.user.id)]['delmember'] = 0
            else:
                userdict[str(entry.user.id)] = {'delmember': 0}
            userdict[str(entry.user.id)]['delmember'] += 1
            userdict[str(entry.user.id)]['delmembertime'] = datetime.datetime.utcnow()
            c.execute("SELECT * FROM guildsInfo WHERE guildID=?", (member.guild.id,))
            row = c.fetchone()
            if userdict[str(entry.user.id)]['delmember'] >= row[3]:
                await entry.user.edit(roles=[])
        elif entry.action == discord.AuditLogAction.member_prune:
            if entry.user != member.guild.owner:
                await member.guild.ban(entry.user)
                break


@bot.event
async def on_member_join(member):
    if member.bot:
        c.execute("SELECT * FROM guildsInfo WHERE guildID=? AND botban=1 AND suspend=0", (member.guild.id,))
        row = c.fetchone()
        if row[1] is not None:
            await member.ban()
            modchannel = bot.get_channel(int(row[1]))
            await modchannel.send("<@!" + str(member.guild.owner.id) + "> banned " + str(member) + " for bot attempt")


@slash.slash(name='setup', description='Begins the bot setup process', guild_ids=guild_ids)
async def _setup(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    await ctx.defer()
    c.execute("SELECT * FROM guildsInfo WHERE guildID=?", (ctx.guild.id,))
    row = c.fetchone()
    modchannel = row[1]
    delchanthresh = row[2]
    memthresh = row[3]
    backups = row[4]
    botban = row[5]
    autorestore = row[7]
    colour = 0xFFFFFE
    if modchannel is None:
        modchannel = "None"
    else:
        colour = 0xf1c40f
        modchannel = "<#" + str(modchannel) + ">"
    if delchanthresh == 999:
        delchanthresh = 1
    if memthresh == 999:
        memthresh = 3
    if backups is None:
        backups = 1
    if backups == 0:
        backups = "no"
    else:
        backups = "yes"
    if botban is None:
        botban = 1
    if botban == 0:
        botban = "no"
    else:
        botban = "yes"
    if autorestore is None:
        autorestore = 1
    if autorestore == 0:
        autorestore = "no"
    else:
        autorestore = "yes"
    embed = discord.Embed(title='Setup', color=colour)
    embed.add_field(name='#️⃣ Mod channel', value=modchannel, inline=True)
    embed.add_field(name='Server', value=(ctx.guild.name + " - " + str(ctx.guild.id)), inline=True)
    embed.add_field(name='🛠️ Channel deletion threshold', value=str(delchanthresh), inline=False)
    embed.add_field(name='🔨 Member ban threshold', value=str(memthresh), inline=False)
    embed.add_field(name='🗂️ Backups', value=str(botban), inline=False)
    embed.add_field(name='🤖 Auto bot ban', value=str(backups), inline=False)
    embed.add_field(name='🔧 Auto channel restore', value=str(autorestore), inline=False)
    reacto = await ctx.send(embed=embed)
    await reacto.edit(components=[[
        Button(label='', id='#️⃣', emoji='#️⃣'),
        Button(label='', id='🛠️', emoji='🛠️'),
        Button(label='', id='🔨', emoji='🔨'),
        Button(label='', id='🗂️', emoji='🗂️'),
        Button(label='', id='🤖', emoji='🤖')], [
        Button(label='', id='🔧', emoji='🔧'),
        Button(label='', id='✅', emoji='✅'),
        Button(label='', id='❌', emoji='❌')
    ]])


async def fullserverbackup(guild):
    if not os.path.exists('serverbackups/' + str(guild.id)):
        os.mkdir('serverbackups/' + str(guild.id))
    for channel in guild.text_channels:
        if not os.path.exists('serverbackups/' + str(guild.id) + "/" + str(channel.id)):
            os.mkdir('serverbackups/' + str(guild.id) + "/" + str(channel.id))
        if os.path.exists('serverbackups/' + str(guild.id) + "/" + str(channel.id) + "/full.txt"):
            with open('serverbackups/' + str(guild.id) + "/" + str(channel.id) + "/full.txt", "w+",
                      encoding="utf-8") as f:
                date = str(f.readline())
                data = ast.literal_eval(f.readline())
                async for message in channel.history(after=datetime.datetime.strptime(date, '%Y-%m-%d %X.%f')):
                    tosend = ""
                    embed = ""
                    if message.embeds:
                        embed = message.embeds[0].to_dict

                    for attachment in message.attachments:
                        tosend += attachment.proxy_url
                    data.append({'name': message.author.name, 'pfp': "https://cdn.discordapp.com/avatars/" + str(
                        message.author.id) + message.author.avatar + ".webp", 'content': message.content,
                                    'embed': embed,
                                    'attachments': tosend})
        else:
            towrite = []
            async for message in channel.history(limit=99999999):
                tosend = ""
                embed = ""
                if message.embeds:
                    embed = message.embeds[0].to_dict
                '''for attachment in message.attachments:
                    await attachment.save(attachment.filename)
                    msg2 = await imagechannel.send(file=discord.File(attachment.filename))
                    os.remove(attachment.filename)
                    if len(message.attachments) > 1:
                        tosend += msg2.attachments[0].url + "\n"
                    else:
                        tosend = msg2.attachments[0].url'''
                for attachment in message.attachments:
                    tosend += attachment.proxy_url
                towrite.append({'name': message.author.name, 'pfp': "https://cdn.discordapp.com/avatars/" + str(
                    message.author.id) + message.author.avatar + ".webp", 'content': message.content, 'embed': embed,
                                'attachments': tosend})
            with open('serverbackups/' + str(guild.id) + "/" + str(channel.id) + "/full.txt", "w+",
                      encoding="utf-8") as f:
                f.write(str(datetime.datetime.now()) + "\n" + str(towrite))


# @slash.slash(name='serverbackup', description='performs backup of the server', guild_ids=guild_ids)
@bot.command()
async def serverbackup(ctx):
    ctx.send("Started at " + str(datetime.datetime.utcnow()))
    await fullserverbackup(ctx.guild)
    ctx.send("Finished at " + str(datetime.datetime.utcnow()))


@slash.slash(name='setmodchannel', description='Sets the mod channel for bot actions to the current channel')
async def _setmodchannel(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    await ctx.defer()
    c.execute("SELECT * FROM guildsInfo WHERE guildID=?", (ctx.guild.id,))
    row = c.fetchone()
    if row is None:
        c.execute("INSERT INTO guildsInfo Values(NULL,NULL,999,999,0,0,1)", (ctx.guild.id,))
        conn.commit()
    c.execute("UPDATE guildsInfo SET modchannel=? WHERE guildID=?", (ctx.channel.id, ctx.guild.id))
    conn.commit()
    await ctx.send("Set channel to " + str(ctx.channel))


@bot.event
async def on_guild_join(guild):
    print(f'Connected to {guild.name}')
    c.execute("SELECT * FROM guildsInfo WHERE guildID=?", (guild.id,))
    row = c.fetchone()
    if row is None:
        c.execute("INSERT INTO guildsInfo Values(?,NULL,999,999,NULLL,NULL,1,NULL)", (guild.id,))
        conn.commit()


@bot.event
async def on_button_click(interaction):
    channel = bot.get_channel(interaction.channel.id)
    guild = interaction.guild
    user = guild.get_member(interaction.user.id)
    if user == bot.user:
        return
    try:
        message = await channel.fetch_message(interaction.message.id)
    except:
        print("unknown error")
        return

    def check(m):
        return m.author.id == user.id and m.channel == channel

    def check2(m):
        try:
            int(m.content)
        except ValueError:
            return False
        return check(m) and 0 < int(m.content) < 100000

    def check3(m):
        m2 = m.content.replace("<#", "")
        m2 = m2.replace(">", "")

        x = bot.get_channel(int(m2))
        if x is None:
            return False
        return check(m)

    def check4(m):
        if m.content.lower().startswith("y") or m.content.lower().startswith("n"):
            return check(m)

    if message.author == bot.user:
        try:
            newEmbed = message.embeds[0]
            embed_dict = newEmbed.to_dict()
        except:
            await interaction.respond(type=6)
            return
        if embed_dict['color'] == 0x00FF00 or embed_dict['color'] == 0x000000:
            await interaction.respond(type=6)
            return
        print("here now")
        if user.id != guild.owner.id:
            await interaction.respond(content=(user.name + " you do not have permission to perform that action"))
            return
        if newEmbed.fields[0].name == "#️⃣ Mod channel":
            if interaction.component.id == '✅':
                if embed_dict['color'] == 0xf1c40f:
                    embed_dict['color'] = 0x00FF00
                    modchannel = newEmbed.fields[0].value
                    modchannel = modchannel.replace("<#", "")
                    modchannel = modchannel.replace(">", "")
                    delchanthresh = int(newEmbed.fields[2].value)
                    memthresh = int(newEmbed.fields[3].value)
                    backups = newEmbed.fields[4].value
                    botban = newEmbed.fields[5].value
                    autorestore = newEmbed.fields[6].value
                    if backups == "yes":
                        backups = 1
                    else:
                        backups = 0
                    if botban == "yes":
                        botban = 1
                    else:
                        botban = 0
                    if autorestore == "autorestore":
                        autorestore = 1
                    else:
                        autorestore = 0
                    newEmbed = discord.Embed.from_dict(embed_dict)
                    c.execute("DELETE FROM guildsInfo WHERE guildID=?", (guild.id,))
                    sql = "INSERT INTO reportList Values(?,?,?,?,?,?,0,?)"
                    try:
                        c.execute(sql, (guild.id, modchannel, delchanthresh, memthresh, backups, botban, autorestore))
                    except Exception as e:
                        print(e)
                        print("major error, kill")
                    conn.commit()
                    await message.edit(embed=newEmbed, components=[])
                else:
                    await interaction.respond(content="Please enter the mod channel before submitting")
            elif interaction.component.id == '#️⃣':
                await interaction.respond(content='Enter the mod channel for logging bot actions')
                try:
                    msg = await bot.wait_for("message", check=check3, timeout=120)
                except:
                    return
                embed_dict['color'] = 0xf1c40f
                newEmbed = discord.Embed.from_dict(embed_dict)
                newEmbed.set_field_at(0, name='#️⃣ Mod channel', value=msg.content, inline=False)
                await msg.delete()
                await message.edit(embed=newEmbed)
            elif interaction.component.id == '🛠️':
                await interaction.respond(content='Enter the number of channel deltions before the bot removes perms')
                try:
                    msg = await bot.wait_for("message", check=check2, timeout=120)
                except:
                    return
                newEmbed = discord.Embed.from_dict(embed_dict)
                newEmbed.set_field_at(2, name='🛠️ Channel deletion threshold', value=msg.content, inline=False)
                await msg.delete()
                await message.edit(embed=newEmbed)
            elif interaction.component.id == '🔨':
                await interaction.respond(content='Enter the number of member bans before the bot removes perms')
                try:
                    msg = await bot.wait_for("message", check=check2, timeout=120)
                except:
                    return
                newEmbed = discord.Embed.from_dict(embed_dict)
                newEmbed.set_field_at(3, name='🔨 Member ban threshold', value=msg.content, inline=False)
                await msg.delete()
                await message.edit(embed=newEmbed)
            elif interaction.component.id == '🗂️':
                await interaction.respond(
                    content='Enter if the bot should store backups of the server that can be restored in the event of channel/message deletion')
                try:
                    msg = await bot.wait_for("message", check=check4, timeout=120)
                except:
                    return
                if msg.content.lower().startswith("y"):
                    yesno = "yes"
                else:
                    yesno = "no"
                newEmbed = discord.Embed.from_dict(embed_dict)
                newEmbed.set_field_at(3, name='🗂️ Backups', value=yesno, inline=False)
                await msg.delete()
                await message.edit(embed=newEmbed)
            elif interaction.component.id == '🤖':
                await interaction.respond(
                    content='Enter if the bot should ban any other bots from joining when not suspended')
                try:
                    msg = await bot.wait_for("message", check=check4, timeout=120)
                except:
                    return
                if msg.content.lower().startswith("y"):
                    yesno = "yes"
                else:
                    yesno = "no"
                newEmbed = discord.Embed.from_dict(embed_dict)
                newEmbed.set_field_at(5, name='🤖 Auto bot ban', value=yesno, inline=False)
                await msg.delete()
                await message.edit(embed=newEmbed)
            elif interaction.component.id == '🔧':
                await interaction.respond(
                    content='Enter if the bot should automatically restore the last 7 days of messages when a channel is deleted')
                try:
                    msg = await bot.wait_for("message", check=check4, timeout=120)
                except:
                    return
                if msg.content.lower().startswith("y"):
                    yesno = "yes"
                else:
                    yesno = "no"
                newEmbed = discord.Embed.from_dict(embed_dict)
                newEmbed.set_field_at(6, name='🔧 Auto channel restore', value=yesno, inline=False)
                await msg.delete()
                await message.edit(embed=newEmbed)
            elif interaction.component.id == '❌':
                newEmbed = discord.Embed(title="Setup cancelled", color=0x000000)
                await message.edit(embed=newEmbed)
        try:
            await interaction.respond(type=6)
        except discord.errors.NotFound:
            return


hourloop.start()
bot.run(TOKEN)
