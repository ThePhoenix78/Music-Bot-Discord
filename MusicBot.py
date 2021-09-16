#  coding: utf-8
import re, urllib.parse, urllib.request, sys
from discord import FFmpegPCMAudio, PCMVolumeTransformer, File
from discord.ext import commands, tasks
from random import choice, shuffle
from yt_dlp import YoutubeDL
from discord.utils import get
from json import load, dumps
from mutagen.mp3 import MP3
from pathlib import Path
from time import sleep
import os.path
import discord


version = "1.2.3"
prefix = "!"
bot_token = "YOUR TOKEN HERE"

intents = discord.Intents.default()
# intents.presences = True
intents.members = True
client = commands.Bot(command_prefix=prefix, intents=intents)

msgnofound = "Error! No music was found"
serv_list: dict = {}

depart = os.getcwd().replace("\\", "/")


music_dir = f"{depart}/Musica"
playlist_dir = f"{music_dir}/playlists"
down_dir = f"{music_dir}/random"

help_msg = """
`/!\ IMPORTANT NOTE! this bot will load all the musics he know containing the keys words and set it as a playlist /!\`

>>> Commands

> Music <

- play (music/link) : will play the music
- next : will go to the next song
- pre / previous : will go for the previous song
- add (music/link) : will add a music to the playlist
- playnext (music/link) : will add the next music to the queue and come back to the original playlist
- pause : will pause the music
- resume : will resume the music
- join : will join the voice chat
- leave : will leave the voice chat
- deco : will disconnect all the members of the current voice chat
- vol (int) : will change the volume of the bot
- loop : will play the same music in loop
- w / what : will show the the informations about the music
- sf / sendfile : will send the music as a mp3 format

> Playlists <

Yeah! this bot can also manage playlists!

- pl (music) (playlist name) : will add the music to the playlist
- ppl (playlist name) : play a playlist
- apl (playlist name) : will play the playlist after
- lpl : list of all the playlists
- rpl (playlist name) : will read the content of the playlist

"""

try:
    os.mkdir(music_dir)
except FileExistsError:
    pass

try:
    os.mkdir(playlist_dir)
except FileExistsError:
    pass

try:
    os.mkdir(down_dir)
except FileExistsError:
    pass


# ----------------------------MOTEUR DE RECHERCHE-------------------------------

def convertir(elem):
    testouet = 0
    if " || " in elem:
        elem = elem.split("||")
        for i in range(len(elem)):
            elem[i] = elem[i].strip().split(" ")
        testouet = 1

    elif " not " in elem:
        value = elem.split()
        elem = elem.split("not")
        notL = 0

        for v in range(len(value)):
            if value[v].startswith("not"):
                notL = v
                break

        for i in range(len(elem)):
            elem[i] = elem[i].strip().split(" ")

        testouet = (2, notL)

    else:
        elem = elem.split()

    return elem, testouet


def recherche(changement, test=False):
    liste = []

    if test in (1, 2):
        for dossier,  sous_dossiers,  fichiers in os.walk(music_dir):
            for fichier in fichiers:
                for elem in changement:
                    j = 0
                    for i in range(len(elem)):
                        if (str(elem[i]).lower() in fichier.lower()) and fichier.endswith(".mp3"):
                            j += 1
                    if j == len(elem):
                        liste.append(fichier)

    if isinstance(test, tuple):
        for dossier,  sous_dossiers,  fichiers in os.walk(music_dir):
            for fichier in fichiers:
                for elem in changement:
                    j = 0
                    for i in range(len(elem)):
                        if (str(elem[i]).lower() in fichier.lower() and i != test[1]) and fichier.endswith(".mp3"):
                            j += 1
                    if j == len(elem):
                        liste.append(fichier)

    else:
        for dossier,  sous_dossiers,  fichiers in os.walk(music_dir):
            for fichier in fichiers:
                i = 0
                j = 0
                while i < len(changement):
                    if str(changement[i]).lower() in fichier.lower() and fichier.endswith(".mp3"):
                        j += 1
                    i += 1
                if j == len(changement):
                    liste.append(fichier)
    return liste

def ranchercher(changement):
    for dossier, sous_dossiers, fichiers in os.walk(music_dir):
        for fichier in fichiers:
            if changement.lower() in fichier.lower() and fichier.endswith(".mp3"):
                return f"{dossier}/{fichier}".replace("\\", "/")
    return None


def telecharger(url):
    url = url.replace("```", "").replace("`", "")

    if ("=" in url and "/" in url and " " not in url) or ("/" in url and " " not in url):

        if "=" in url and "/" in url:
            ide = url.rsplit("=", 1)
            ide = ide[-1]
            music = ide
        elif "/" in url:
            ide = url.rsplit("/")
            ide = ide[-1]
            music = ide

        if ranchercher(music):
            return music

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
                }],
            'extract-audio': True,
            # 'outtmpl': f"{down_dir}/{music}.mp3",
            }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', None)
            ydl.cache.remove()

        for name in os.listdir():
            if video_title in name:
                os.system("move /Y {} {}".format(f'"{name}"', f'"{down_dir}/{video_title}-{music}.mp3"'))

        url = music

    return url

def search_internet_music(music_name):
    query_string = urllib.parse.urlencode({"search_query": music_name})
    formatUrl = urllib.request.urlopen("https://www.youtube.com/results?" + query_string)

    search_results = re.findall(r"watch\?v=(\S{11})", formatUrl.read().decode())
    clip2 = "https://www.youtube.com/watch?v=" + "{}".format(search_results[0])
    return telecharger(clip2)

# ------------------------CLASSE------------------------------------------------

class MusicManager:
    def __init__(self, ctx):
        self.reset_values()

        self.guild = ctx
        self.path_play = f"{playlist_dir}/{self.guild.name}.json"


    def reset_values(self):
        self.playlist = None
        self.next_playlist = []

        self.current_music = ""
        self.path_to_current_music = ""

        self.filter = ""
        self.search: list = []
        self.temp_search: list = []

        self.index = 0
        self.index_pl = 0

        self.playing = False
        self.volume = 1

        self.pause = False
        self.looping = False

        self.timer_music: int = 0
        self.len_music: int = 99
        self.digit_timer: str = ""


    def get_playlist_file(self):
        with open(self.path_play, "r", encoding="utf8") as fic:
            return load(fic)


    def get_playlist_name(self):
        with open(self.path_play, "r", encoding="utf8") as fic:
            return load(fic).keys()


    def playlist_exist(self, name):
        return name in self.get_playlist_file().keys()


    def load_playlist_file(self, name: str=None):
        with open(self.path_play, "r", encoding="utf8") as fic:
            info = load(fic)
        for key, value in info.items():
            if key == name:
                return value
        return None

    def add_song_to_playlist(self, name, music):
        play = self.load_playlist_file(name)

        music = telecharger(music)
        elem, testouet = convertir(music)
        m = recherche(elem, testouet)

        if not m:
            t = search_internet_music(music)
            elem, testouet = convertir(t)
            m = recherche(elem, testouet)

        if not m:
            return

        if not play:
            self.add_playlist_file(name, [m[0]])
            return m[0]

        play.append(m[0])
        self.update_playlist_file(name, play)
        return m[0]

    def remove_song_from_playlist(self, name, music):
        play = self.load_playlist_file(name)

        elem, testouet = convertir(music)
        m = recherche(elem, testouet)

        if not play or not m:
            return None

        try:
            play.remove(m[0])
            self.update_playlist_file(name, play)
            return m[0]
        except Exception:
            pass


    def delete_playlist_file(self, name):
        with open(self.path_play, "r", encoding="utf8") as fic:
            info = load(fic)

        for key, value in info.items():
            if key == name:
                del(info[key])
                break

        with open(self.path_play, "w", encoding="utf8") as fic:
            fic.write(dumps(info, sort_keys=True, indent=4))


    def add_playlist_file(self, name, new_list):
        with open(self.path_play, "r", encoding="utf8") as fic:
            info = load(fic)

        info[name] = new_list

        with open(self.path_play, "w", encoding="utf8") as fic:
            fic.write(dumps(info, sort_keys=True, indent=4))


    def update_playlist_file(self, name, new_list):
        with open(self.path_play, "r", encoding="utf8") as fic:
            info = load(fic)

        for key, value in info.items():
            if key == name:
                info[key] = new_list

                with open(self.path_play, "w", encoding="utf8") as fic:
                    fic.write(dumps(info, sort_keys=True, indent=4))

                return True
        return False


    async def lire_playlist(self, ctx, name):
        self.index_pl = 0
        self.playlist = self.load_playlist_file(name)

        if not self.playlist:
            await ctx.send("Error! playlist not found")
            return

        shuffle(self.playlist)

        if lecteur(self):
            await ctx.send(f"Playing: {self.current_music} [{self.digit_timer}]")


    @tasks.loop(seconds=1)
    async def time_music(self):
        if (self.timer_music < self.len_music and self.playing):
            if self.pause:
                return

            self.timer_music += 1
            return

        self.playing = False

        if self.timer_music >= self.len_music:
            if self.playlist:
                if self.index_pl+1 < len(self.playlist)-1:
                    self.index_pl += 1

                elif self.next_playlist and self.index_pl+1 >= len(self.playlist)-1:
                    self.playlist = self.next_playlist.pop(0)
                    shuffle(self.playlist)
                    self.index_pl = 0

                else:
                    self.index_pl = 0
                    shuffle(self.playlist)

            elif not self.temp_search:
                if self.index+1 < len(self.search)-1:
                    self.index += 1
                else:
                    self.index = 0

            self.timer_music = 0
            lecteur(self)


def lecteur(serv, music: str=None, replay=False):
    if replay:
        pass

    elif serv.looping:
        serv.current_music = serv.search[serv.index]

    elif serv.playlist:
        serv.current_music = serv.playlist[serv.index_pl]

    elif serv.temp_search:
        serv.current_music = serv.temp_search.pop(0)

    elif music:
        serv.index = 0
        serv.search = music

        if not serv.search:
            return False

        serv.filter = music
        shuffle(serv.search)
        serv.current_music = serv.search[serv.index]

    else:
        serv.current_music = serv.search[serv.index]


    serv.path_to_current_music = ranchercher(serv.current_music)
    if not serv.path_to_current_music:
        return False

    serv.playing = False
    voice = get(client.voice_clients,  guild=serv.guild)

    if voice and voice.is_playing():
        voice.stop()

    voice.play(FFmpegPCMAudio(serv.path_to_current_music))
    voice.source = PCMVolumeTransformer(voice.source)
    voice.source.volume = serv.volume

    audio = MP3(serv.path_to_current_music)
    serv.len_music = audio.info.length

    serv.timer_music = 0
    sleep(0.7)
    serv.playing = True

    serv.digit_timer = str(int(serv.len_music/60))+" : "+str(int(serv.len_music % 60))
    return True


# -----------------------------INFO STATISTIQUES--------------------------------


@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game("Music go!"), status=discord.Status.online)
    servers = client.guilds

    for server in servers:
        serv_list[server.name] = MusicManager(server)
        if not Path(f'{playlist_dir}/{server.name}.json').exists():
            a = open(f'{playlist_dir}/{server.name}.json', "w")
            a.write("{}")
            a.close()
        serv_list[server.name].time_music.start()

    change_status.start()
    print("version : ", f"{os.path.basename(sys.argv[0])} {version}")
    print("Logged in as : ", client.user.name)
    print("ID : ", client.user.id)


@client.event
async def on_guild_join(ctx):
    servers = client.guilds
    for server in servers:
        if server not in serv_list.keys():
            serv_list[server.name] = MusicManager(server)
            if not Path(f'{playlist_dir}/{server.name}.json').exists():
                a = open(f'{playlist_dir}/{server.name}.json', "w")
                a.write("{}")
                a.close()
            serv_list[server.name].time_music.start()


@client.event
async def on_command_error(ctx,  error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Please pass in all required arguments')


# -----------------------------COMMANDE STATUT VOCAL----------------------------


@client.command()
async def ping(ctx):
    await ctx.send(f':ping_pong: **Pong !** {round(client.latency * 1000)}ms')


@client.command(pass_context=True, aliases=["p2"])
async def play(ctx, *, music: str):
    serv = serv_list[ctx.guild.name]
    serv.reset_values()

    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients,  guild=ctx.guild)

    if not voice or (voice and not voice.is_connected()):
        channel = ctx.message.author.voice.channel

        if voice and voice.is_connected():
            await voice.move_to(channel)
        else:
            voice = await channel.connect()

        await voice.disconnect()

        if voice and voice.is_connected():
            await voice.move_to(channel)
            print(f"The bot is connected to {channel}")
        else:
            voice = await channel.connect()
            print(f"The bot is connected to {channel}")

        await ctx.send(f"Joined {channel}")

    await ctx.send("Getting everything ready now")

    music = telecharger(music)
    elem, testouet = convertir(music)
    search = recherche(elem, testouet)

    if not search:
        await ctx.send(msgnofound+" search for it on the internet")
        music = search_internet_music(music)
        elem, testouet = convertir(music)
        search = recherche(elem, testouet)

    if not search:
        await ctx.channel.send(msgnofound)
        return

    if lecteur(serv, search):
        await ctx.send(f"Playing: {serv.current_music} [{serv.digit_timer}]")
    else:
        await ctx.channel.send(msgnofound)


@client.command()
async def join(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients,  guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()

    await voice.disconnect()

    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()

    await ctx.send(f"Joined {channel}")

    return voice


@client.command()
async def leave(ctx):
    serv = serv_list[ctx.guild.name]

    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients,  guild=ctx.guild)

    serv.reset_values()

    if voice and voice.is_playing():
        voice.stop()

    if voice and voice.is_connected():
        await voice.disconnect()
        await ctx.send(f"Left {channel}")
    else:
        await ctx.send("I don't think I am in a voice channel")


@client.command()
async def next(ctx):
    serv = serv_list[ctx.guild.name]
    await ctx.send("Getting everything ready now")
    if serv.playlist:
        if serv.index_pl+1 < len(serv.playlist)-1:
            serv.index_pl += 1

        elif serv.next_playlist and serv.index_pl+1 >= len(serv.playlist)-1:
            serv.playlist = serv.next_playlist.pop(0)
            shuffle(serv.playlist)
            serv.index_pl = 0

        else:
            serv.index_pl = 0
            shuffle(serv.playlist)

    elif not serv.temp_search:
        if serv.index+1 < len(serv.search)-1:
            serv.index += 1
        else:
            serv.index = 0

    if lecteur(serv):
        await ctx.send(f"Playing: {serv.current_music} [{serv.digit_timer}]")


@client.command(pass_context=True, aliases=["volume"])
async def vol(ctx, nb):
    serv = serv_list[ctx.guild.name]
    vol = int(nb)
    vol = vol/10 if vol<=1 else vol/100
    voice = get(client.voice_clients,  guild=ctx.guild)
    voice.source = PCMVolumeTransformer(voice.source)
    voice.source.volume = vol
    serv.volume = vol
    await ctx.send(f"Volume set on {vol}")


@client.command()
async def loop(ctx):
    serv = serv_list[ctx.guild.name]
    if not serv.looping:
        serv.looping = True
    else:
        serv.looping = False

    await ctx.send(f"Set looping on {serv.looping}")


@client.command()
async def replay(ctx):
    serv = serv_list[ctx.guild.name]
    await ctx.send("Getting everything ready now")

    if lecteur(serv, replay=True):
        await ctx.send(f"Playing: {serv.current_music} [{serv.digit_timer}]")


@client.command(aliases=["previous"])
async def pre(ctx):
    serv = serv_list[ctx.guild.name]

    await ctx.send("Getting everything ready now")
    if serv.playlist:
        if serv.index_pl-1 < 0:
            serv.index_pl = len(serv.playlist)-1
        else:
            serv.index_pl -= 1

    if not serv.temp_search:
        if serv.index-1 < 0:
            serv.index = len(serv.search)-1
        else:
            serv.index -= 1

    if lecteur(serv):
        await ctx.send(f"Playing: {serv.current_music} [{serv.digit_timer}]")


@client.command(aliases=["w"])
async def what(ctx):
    serv = serv_list[ctx.guild.name]
    val = serv.timer_music if serv.timer_music > 0 else 0
    await ctx.send(f"Music: {serv.current_music} [{int(val/60)} : {int(val % 60)}/{serv.digit_timer}]")


@client.command()
async def playnext(ctx, *, music):
    serv = serv_list[ctx.guild.name]

    music = telecharger(music)
    elem, testouet = convertir(music)
    search = recherche(elem, testouet)

    if not search:
        await ctx.send(msgnofound+" search for it on the internet")
        music = search_internet_music(music)
        elem, testouet = convertir(music)
        search = recherche(elem, testouet)

    if not search:
        await ctx.send(msgnofound)

    serv.temp_search = search
    await ctx.send(f"Added {music}")


@client.command()
async def add(ctx, *, music):
    serv = serv_list[ctx.guild.name]

    music = telecharger(music)
    elem, testouet = convertir(music)
    search = recherche(elem, testouet)

    if not search:
        await ctx.send(msgnofound+" search for it on the internet")
        music = search_internet_music(music)
        elem, testouet = convertir(music)
        search = recherche(elem, testouet)

    if not search:
        await ctx.send(msgnofound)

    serv.search = search
    await ctx.send(f"Added {music}")


@client.command()
async def pause(ctx):
    serv = serv_list[ctx.guild.name]

    voice = get(client.voice_clients,  guild=ctx.guild)

    if voice and voice.is_playing():
        serv.pause = True
        voice.pause()
        await ctx.send("Music paused")
    else:
        await ctx.send("Music not playing failed pause")


@client.command()
async def resume(ctx):
    serv = serv_list[ctx.guild.name]

    voice = get(client.voice_clients,  guild=ctx.guild)

    if voice and voice.is_paused():
        serv.pause = False
        voice.resume()
        await ctx.send("Resumed music")
    else:
        await ctx.send("Music is not paused")


@client.command(aliases=["stop"])
async def stopmusic(ctx):
    serv = serv_list[ctx.guild.name]

    voice = get(client.voice_clients,  guild=ctx.guild)

    if voice and voice.is_playing():
        voice.stop()
        serv.reset_values()
        await ctx.send("Music stopped")

    else:
        await ctx.send("No music playing failed to stop")


# --------------- playlistes --------------


@client.command()
async def ppl(ctx, *, name):
    serv = serv_list[ctx.guild.name]

    serv.index_pl = 0
    serv.playlist = serv.load_playlist_file(name)

    if not serv.playlist:
        await ctx.send("Error! playlist not found")
        return

    shuffle(serv.playlist)

    voice = get(client.voice_clients,  guild=ctx.guild)

    if not voice or (voice and not voice.is_connected()):
        channel = ctx.message.author.voice.channel

        if voice and voice.is_connected():
            await voice.move_to(channel)
        else:
            voice = await channel.connect()

        await voice.disconnect()

        if voice and voice.is_connected():
            await voice.move_to(channel)
            print(f"The bot is connected to {channel}")
        else:
            voice = await channel.connect()
            print(f"The bot is connected to {channel}")

        await ctx.send(f"Joined {channel}")

    if lecteur(serv):
        await ctx.send(f"Playing: {serv.current_music} [{serv.digit_timer}]")
        await ctx.send(f"Playing {name} playlist")


@client.command()
async def apl(ctx, *, music):
    serv = serv_list[ctx.guild.name]
    serv.next_playlist.append(serv.load_playlist_file(music))

    if not serv.playlist:
        await ctx.send("Error! playlist not found")
        return False

    await ctx.send(f"Added: {music} to queue!")
    return True


@client.command()
async def rpl(ctx, name):
    serv = serv_list[ctx.guild.name]

    val = "```"+"\n".join(serv.load_playlist_file(name))+"```"

    if len(val) >= 1950:
        val = val.replace('```', '')
        with open(f"{name}.txt", 'w', encoding="utf8") as fp:
            fp.write(val)

        with open(f"{name}.txt", 'rb') as fb:
            await ctx.channel.send(file=discord.File(fb,  f"{name}.txt"))
        os.remove(f"{name}.txt")
    else:
        await ctx.send(val)


@client.command()
async def lpl(ctx):
    serv = serv_list[ctx.guild.name]
    await ctx.send("```"+"\n".join(serv.get_playlist_name())+"```")


@client.command()
async def delpl(ctx, name):
    serv = serv_list[ctx.guild.name]
    serv.delete_playlist_file(name)
    await ctx.send(f"playlist {name} has been removed")


@client.command()
async def pl(ctx, *, music: str):
    serv = serv_list[ctx.guild.name]
    music = music.rsplit(" ", 1)
    name = music[1]
    music = music[0]

    song = serv.add_song_to_playlist(name, music)
    if song:
        await ctx.send(f"Added {song} to playlist")
    else:
        await ctx.send("Error!")

@client.command()
async def dpl(ctx, *, music):
    serv = serv_list[ctx.guild.name]
    music = music.rsplit(" ", 1)
    name = music[1]
    music = music[0]

    song = serv.remove_song_from_playlist(name, music)

    if song:
        await ctx.send(f"Removed {song} from playlist")
    else:
        await ctx.send("Error!")

# ---------------------------------------

@client.command()
async def deco(ctx):
    try:
        channel = ctx.message.author.voice.channel
    except Exception:
        return

    voice = get(client.voice_clients,  guild=ctx.guild)

    if voice and voice.is_playing():
        voice.stop()

    if voice and voice.is_connected():
        await voice.disconnect()

    victims = ctx.guild.members

    kick_channel = await ctx.guild.create_voice_channel("kick")

    for victim_member in victims:
        try:
            if victim_member.voice.channel == channel:
                await victim_member.move_to(kick_channel,  reason="deco")
        except Exception:
            pass

    await kick_channel.delete()

# --------------------------------COMMANDES BASE--------------------------------


@client.command()
async def size(ctx, *, message):
    elem, testouet = convertir(message)
    a = recherche(elem, testouet)
    await ctx.channel.send(f"{len(a)} results found")


@client.command(aliases=["list"])
async def liste(ctx, *, message="."):
    elem, testouet = convertir(message)
    a = recherche(elem, testouet)
    playliste = []
    if len(a) <= 10:
        for i in range(len(a)):
            playliste.append(a[i])
            await ctx.channel.send("```"+str(a[i])+"```")
    else:
        for i in range(10):
            ran = choice(a)
            if ran not in playliste:
                playliste.append(ran)
                await ctx.channel.send("```"+str(ran)+"```")
            else:
                i -= 1
            sleep(0.2)


@client.command(aliases=["sendfile"])
async def sf(ctx, *, music: str):
    await ctx.send("Getting everything ready now")

    music = telecharger(music)

    elem, testouet = convertir(music)
    search = recherche(elem, testouet)

    if not search:
        await ctx.send(msgnofound+" search for it on the internet")
        music = search_internet_music(music)
        elem, testouet = convertir(music)
        search = recherche(elem, testouet)

    if not search:
        await ctx.send(msgnofound)
        return

    file = choice(search)
    b = ranchercher(file)

    if os.path.getsize(b) >= 8000000:
        await ctx.send(f"The file : {file} is too heavy")
        return

    await ctx.send(f"sending file {file}")
    with open(b,  'rb') as fp:
        await ctx.channel.send(file=File(fp,  file))


@client.command(pass_context=True)
async def moveall(ctx, *, chan=""):

    victim = ctx.guild.members
    val = ctx.guild.voice_channels

    for i in range(len(val)):
        if str(chan) == str(val[i]):
            kick_channel = val[i]
            break
        elif str(chan).upper() in str(val[i]).upper():
            kick_channel = val[i]
            break

    for i in range(len(victim)):
        victim_member = victim[i]
        try:
            if victim_member.voice.channel in val and ("AFK" not in str(victim_member.voice.channel).upper()):
                await victim_member.move_to(kick_channel, reason="")
        except:
            pass


# ------------------------------------Tasks-------------------------------------


@client.command()
async def reboot(ctx):
    serv = serv_list[ctx.guild.name]

    await client.change_presence(activity=discord.Game("Shutting down..."), status=discord.Status.dnd)
    voice = get(client.voice_clients,  guild=ctx.guild)

    if voice and voice.is_playing():
        voice.stop()

    if voice and voice.is_connected():
        await voice.disconnect()

    serv.reset_values()

    await ctx.send("Restarting bot")
    os.execv(sys.executable, ["None", os.path.basename(sys.argv[0])])


dis_status = ['waiting for you', "Music... Music everywhere"]
iter = 0
@tasks.loop(seconds=127)
async def change_status():
    global iter
    await client.change_presence(activity=discord.Game(dis_status[iter]))
    iter += 1
    if iter > len(dis_status)-1:
        iter = 0


client.run(bot_token)
