import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
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
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_permission
from discord_slash.model import SlashCommandPermissionType
from discord_slash.utils.manage_commands import create_option
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType

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


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    for guild in bot.guilds:
        print(f'Connected to {guild.name}')
    DiscordComponents(bot)


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
            userdict[str(entry.user.id)]['delchanneltime'] = datetime.datetime.now()
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
            userdict[str(entry.user.id)]['delmembertime'] = datetime.datetime.now()
            c.execute("SELECT * FROM guildsInfo WERE guildID=?", (member.guild.id,))
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
        c.execute("SELECT * FROM guildsInfo WERE guildID=? AND botban=1 AND suspend=0", (member.guild.id,))
        row = c.fetchone()
        if row[1] is not None:
            await member.ban()
            modchannel = bot.get_channel(int(row[1]))
            await modchannel.send("<@!"+str(member.guild.owner.id)+"> banned "+str(member)+" for bot attempt")


@slash.slash(name='setup', description='Begins the bot setup process')
async def _setup(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    await ctx.defer()
    embed = discord.Embed(title='Setup')
    await ctx.send(embed=embed)


@slash.slash(name='setmodchannel', description='Sets the mod channel for bot actions to the current channel')
async def _setmodchannel(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("You do not have the permissions to use that command", hidden=True)
        return
    await ctx.defer()
    c.execute("SELECT * FROM guildsInfo WHERE guildID=?", (ctx.guild.id,))
    row = c.fetchone()
    if row is None:
        c.execute("INSERT INTO guildsInfo Values(?,NULL,999,999,0,0,1)", (ctx.guild.id,))
        conn.commit()
    c.execute("UPDATE guildsInfo SET modchannel=? WHERE guildID=?", (ctx.channel.id, ctx.guild.id))
    conn.commit()
    await ctx.send("Set channel to " + str(ctx.channel))


@bot.event
async def on_guild_join(guild):
    print(f'Connected to {guild.name}')
    c.execute("SELECT * FROM guildsInfo WERE guildID=?", (guild.id,))
    row = c.fetchone()
    if row is None:
        c.execute("INSERT INTO guildsInfo Values(?,NULL,999,999,0,0,1)", (guild.id,))
        conn.commit()



bot.run(TOKEN)
