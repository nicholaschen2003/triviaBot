import os
import discord
import re
import time
import asyncio
import json
import random
from difflib import SequenceMatcher
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

def get_song_list(dir):
    files = os.listdir(dir)
    song_list = []
    for filename in files:
        anime = filename.split("____")[1].split("-")[0]
        if anime[-2:] == "TV" or anime[-2:] == "S1" or anime[-2:] == "S2" or anime[-2:] == "S3" or anime[-2:] == "S4" or anime[-2:] == "S5":
            anime = anime[:-2]
        if anime[-3:] == "OVA":
            anime = anime[:-3]
        try:
            test = int(anime[-4:])
            anime = anime[:-4]
        except:
            pass
        s = anime[0].upper()
        for c in anime[1:]:
            if c.isupper():
                s += f" {c}"
            else:
                s += c   
        song_list.append((filename, s))

    return song_list

def split_song_difficulty(song_list):
    easy = []
    medium = []
    hard = []
    impossible = []
    for song in song_list:
        if song[0][0] == "1":
            easy.append(song)
        elif song[0][0] == "2":
            medium.append(song)
        elif song[0][0] == "3":
            hard.append(song)
        else:
            impossible.append(song)
    return easy, medium, hard, impossible

SYMBOL = ">"
CATEGORIES = [x.split(".")[0] for x in os.listdir("categories")]
SONG_LIST = get_song_list("audio-final")
EASY, MEDIUM, HARD, IMPOSSIBLE = split_song_difficulty(SONG_LIST)
ALL = EASY + MEDIUM + HARD + IMPOSSIBLE
DIFFICULTIES = {"Easy": EASY, "Medium": MEDIUM, "Hard": HARD, "Impossible": IMPOSSIBLE, "All": ALL}
NUM_QUESTIONS = []
ZIPPED = []
RATIO = 80
VOLUME = 10
for c in CATEGORIES:
    with open(f"categories/{c}.txt", encoding="utf8") as f:
        qcount = int(len(f.readlines())/2)
        NUM_QUESTIONS.append(qcount)
        ZIPPED.append((c, qcount))
TIMEOUT = 10
DELAY = 5
FORCE_QUIT = False
SKIP = False
GAME_RUNNING = False
with open("rankings.json") as json_file:
    RANKINGS = json.load(json_file)

def check(ans):
    def inner_check(message):
        global FORCE_QUIT
        global SKIP
        global RATIO
        if message.content == f"{SYMBOL}stop":
            FORCE_QUIT = True
        if message.content == f"{SYMBOL}skip":
            SKIP = True
        return (SequenceMatcher(None, message.content.lower(), ans.lower()).ratio() >= RATIO/100 or FORCE_QUIT or SKIP)
    return inner_check

async def start_game(type, n, c, message):
    global CATEGORIES
    global DIFFICULTIES
    global ZIPPED
    global TIMEOUT
    global DELAY
    global RANKINGS
    global FORCE_QUIT
    global SKIP
    global GAME_RUNNING
    global VOLUME

    if type == "q":
        if c.lower() in CATEGORIES:
            f = open(f"categories/{c.lower()}.txt", 'r', encoding='utf8')
            lines = f.readlines()
            try:
                qas = [(lines[i].strip(), lines[i+1].strip()) for i in range(0, len(lines), 2)]
            except:
                qas = [(lines[i].strip(), lines[i+1].strip()) for i in range(0, len(lines)-1, 2)]
            if int(n) <= len(qas):
                sub_qas = random.sample(qas, int(n))
                diff_multiplier = 1
            else:
                await message.channel.send(f"Not enough questions, max is **{len(qas)}**")
                return
        else:
            l = [f"**{x[0]}**: {x[1]} questions" for x in ZIPPED]
            await message.channel.send(f"Category **{c}** not found, valid options are:\n" + "\n".join(l))
            return
    else:
        if f"{c[0].upper()}{c[1:].lower()}" in ["Easy", "Medium", "Hard", "Impossible", "All"]:
            qas = DIFFICULTIES[f"{c[0].upper()}{c[1:].lower()}"]
            if int(n) <= len(qas):
                sub_qas = random.sample(qas, int(n))
                diff_multiplier = list(DIFFICULTIES.keys()).index(f"{c[0].upper()}{c[1:].lower()}") + 1
            else:
                await message.channel.send(f"Not enough songs, max is **{len(qas)}**")
                return
        else:
            l = [f"**{k}**: {len(v)} songs" for k, v in DIFFICULTIES.items()]
            await message.channel.send(f"Difficulty **{c}** not found, valid options are:\n" + "\n".join(l))
            return
    
    if type == "q":
        await message.channel.send(f"Starting game with **{n}** questions and category **{c}**")
    else:
        if TIMEOUT >= 10:
            if message.author.voice:
                vc = await message.author.voice.channel.connect()
            else:
                await message.channel.send(f"Please join a voice channel first!")
                return
        else:
            await message.channel.send(f"Please set the hint delay to be greater than or equal to 10!")
            return
        await message.channel.send(f"Starting song quiz with **{n}** questions and difficulty **{c}**")
        
    GAME_RUNNING = True
    for i, qa in enumerate(sub_qas):
        for j in range(4):
            if not FORCE_QUIT:
                if j == 0:
                    if type == "q":
                        await message.channel.send(f"**Question {i+1}**: {qa[0]}")
                    else:
                        await message.channel.send(f"Now playing **song {i+1}**!")
                        source = discord.FFmpegPCMAudio(f"audio-final/{qa[0]}")
                        source = discord.PCMVolumeTransformer(source, volume=VOLUME/100)
                        vc.play(source)
                        
                    ans = qa[1]
                    start = time.time()
                elif j == 1:
                    await message.channel.send("**Hint 1**: " + re.sub(r'\w', "\_", ans))
                elif j == 2:
                    await message.channel.send("**Hint 2, scrambled**: " + "".join(random.sample(ans, len(ans))))
                elif j == 3:
                    s = ""
                    for word in ans.split(" "):
                        s += ''.join("\_" if i % 2 == 0 else char for i, char in enumerate(word, 1))
                        s += " "
                    await message.channel.send("**Hint 3**: " + s)
                try:
                    msg = await client.wait_for('message', check=check(ans), timeout=TIMEOUT)
                except asyncio.TimeoutError:
                    if j == 3:
                            await message.channel.send(f"Time's up! Correct answer was: **{ans}**.")
                else:
                    if FORCE_QUIT:
                        await message.channel.send(f"Aborting...")
                        if type == "s":
                            await vc.disconnect()
                        break
                    if SKIP:
                        await message.channel.send(f"Correct answer: **{ans}**.")
                        if type == "s":
                            vc.stop()
                        SKIP = False
                        break
                    else:
                        if type == "s":
                            vc.stop()
                        elapsed = time.time() - start
                        await message.channel.send(f"Correct answer: **{ans}**.\n**{msg.author}** correctly answered **{msg.content}** in **{elapsed:.2f}** seconds, earning **{diff_multiplier*(5 - j)}** points!")
                        if str(msg.author) in RANKINGS.keys():
                            RANKINGS[str(msg.author)] += diff_multiplier*(5 - j)
                        else:
                            RANKINGS[str(msg.author)] = diff_multiplier*(5 - j)
                        RANKINGS = dict(sorted(RANKINGS.items(), key=lambda item: item[1], reverse=True))
                        with open("rankings.json", "w") as outfile: 
                            json.dump(RANKINGS, outfile)
                        break
            else:
                break
        if i != len(sub_qas)-1 and not FORCE_QUIT:
            try:
                msg = await client.wait_for('message', check=check(""), timeout=DELAY)
            except asyncio.TimeoutError:
                pass
            else:
                if FORCE_QUIT:
                    await message.channel.send(f"Aborting...")
                    if type == "s":
                        await vc.disconnect()
                    break
    await message.channel.send("End of game!")
    if type == "s":
        await vc.disconnect()
    ranks = "\n".join([f"{i}. {x[0]}: {x[1]}" for i, x in enumerate(RANKINGS.items())])
    await message.channel.send(f"__**Rankings**__:\n{ranks}")
    FORCE_QUIT = False
    GAME_RUNNING = False

@client.event
async def on_ready():
    print(f'Logged on as {client.user}!')

@client.event
async def on_message(message):
    global ZIPPED
    global RATIO
    global VOLUME
    global TIMEOUT
    global DELAY
    global RANKINGS
    global SYMBOL
    global GAME_RUNNING

    if message.author.id == client.user.id:
        return

    elif message.content == f'{SYMBOL}categories':
        l = [f"**{x[0]}**: {x[1]} questions" for x in ZIPPED]
        await message.channel.send("__**Categories**__:\n" + "\n".join(l))

    elif message.content == f'{SYMBOL}difficulties':
        l = [f"**{k}**: {len(v)} songs" for k, v in DIFFICULTIES.items()]
        await message.channel.send("__**Difficulties**__:\n" + "\n".join(l))

    elif x := re.search(f'{SYMBOL}hintdelay (\d*)', message.content):
        TIMEOUT = int(x.group(1))
        await message.channel.send(f"Delay between **hints** is now **{TIMEOUT}** seconds!")

    elif x := re.search(f'{SYMBOL}qdelay (\d*)', message.content):
        DELAY = int(x.group(1))
        await message.channel.send(f"Delay between **questions** is now **{DELAY}** seconds!")

    elif x := re.search(f'{SYMBOL}ct (\d*)', message.content):
        RATIO = int(x.group(1))
        await message.channel.send(f"**Correctness threshold** is now **{RATIO}%**!")

    elif x := re.search(f'{SYMBOL}volume (\d*)', message.content):
        VOLUME = int(x.group(1))
        await message.channel.send(f"**Correctness threshold** is now **{VOLUME}%**!")

    elif x := re.search(f'{SYMBOL}tstart questions (\d*) category (.*)', message.content):
        if GAME_RUNNING:
            await message.channel.send(f"There is already a game running! Please finish that game or cancel it with {SYMBOL}stop first!")
        else:
            await start_game("q", x.group(1), x.group(2), message)

    elif x := re.search(f'{SYMBOL}sstart questions (\d*) difficulty (.*)', message.content):
        if GAME_RUNNING:
            await message.channel.send(f"There is already a game running! Please finish that game or cancel it with {SYMBOL}stop first!")
        else:
            await start_game("s", x.group(1), x.group(2), message)
    
    elif message.content == f'{SYMBOL}rankings':
        ranks = "\n".join([f"{i}. **{x[0]}**: {x[1]}" for i, x in enumerate(RANKINGS.items())])
        await message.channel.send(f"__**Rankings**__:\n{ranks}")

    elif message.content == f'{SYMBOL}resetrankings':
        RANKINGS = {}
        with open("rankings.json", "w") as outfile: 
            json.dump(RANKINGS, outfile)
        await message.channel.send(f"Rankings have been reset!")

    elif x := re.search(f'{SYMBOL}prefix (.*)', message.content):
        SYMBOL = x.group(1)
        await message.channel.send(f"Prefix is now: {SYMBOL}")
    
    elif message.content == f"{SYMBOL}help":
        await message.channel.send(f"""To check available **categories**, use **{SYMBOL}categories**.
To adjust the **delay between hints**, use **{SYMBOL}hintdelay <seconds>**. Current value is **{TIMEOUT}**.
To adjust the **delay between questions**, use **{SYMBOL}qdelay <seconds>**. Current value is **{DELAY}**.
To **check rankings**, use **{SYMBOL}rankings**.
To **reset rankings**, use **{SYMBOL}resetrankings**.
To adjust the **correctness threshold**, use **{SYMBOL}ct <number_between_0_and_100>**. Current value is **{RATIO}**.
To adjust the **volume** of songs played during the song quiz, use **{SYMBOL}volume <number_between_0_and_100>**. Current value is **{VOLUME}**.
To see available **categories** (trivia game), use **{SYMBOL}categories**.
To see available **difficulties** (song quiz), use **{SYMBOL}difficulties**.
To **start a trivia game**, use **{SYMBOL}tstart questions <number_of_questions> category <category_name>**.
To **start a song quiz**, use **{SYMBOL}sstart questions <number_of_questions> difficulty <difficulty_name>**.
To **skip a question** while a game is running, use **{SYMBOL}skip**,
To **end a game** that is currently running, use **{SYMBOL}stop**.
To change the bot's **prefix**, use **{SYMBOL}prefix <new_prefix>** Current value is **{SYMBOL}**.""")
        
client.run(TOKEN)