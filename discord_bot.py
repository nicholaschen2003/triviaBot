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

SYMBOL = ">"
CATEGORIES = [x.split(".")[0] for x in os.listdir("categories")]
NUM_QUESTIONS = []
ZIPPED = []
RATIO = 80
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

@client.event
async def on_ready():
    print(f'Logged on as {client.user}!')

@client.event
async def on_message(message):
    global CATEGORIES
    global NUM_QUESTIONS
    global ZIPPED
    global RATIO
    global TIMEOUT
    global DELAY
    global RANKINGS
    global SYMBOL
    global FORCE_QUIT
    global SKIP
    global GAME_RUNNING

    if message.author.id == client.user.id:
        return

    elif message.content == f'{SYMBOL}categories':
        l = [f"**{x[0]}**: {x[1]} questions" for x in ZIPPED]
        await message.channel.send("__**Categories**__:\n" + "\n".join(l))

    elif x := re.search(f'{SYMBOL}hintdelay (\d*)', message.content):
        TIMEOUT = int(x.group(1))
        await message.channel.send(f"Delay between **hints** is now **{TIMEOUT}** seconds!")

    elif x := re.search(f'{SYMBOL}qdelay (\d*)', message.content):
        DELAY = int(x.group(1))
        await message.channel.send(f"Delay between **questions** is now **{DELAY}** seconds!")

    elif x := re.search(f'{SYMBOL}ct (\d*)', message.content):
        RATIO = int(x.group(1))
        await message.channel.send(f"**Correctness threshold** is now **{RATIO}%**!")

    elif x := re.search(f'{SYMBOL}start questions (\d*) category (.*)', message.content):
        if GAME_RUNNING:
            await message.channel.send(f"There is already a game running! Please finish that game or cancel it with {SYMBOL}stop first!")
        else:
            if x.group(2).lower() in CATEGORIES:
                f = open(f"categories/{x.group(2).lower()}.txt", 'r', encoding='utf8')
                lines = f.readlines()
                try:
                    qas = [(lines[i].strip(), lines[i+1].strip()) for i in range(0, len(lines), 2)]
                except:
                    qas = [(lines[i].strip(), lines[i+1].strip()) for i in range(0, len(lines)-1, 2)]
                if int(x.group(1)) <= len(qas):
                    sub_qas = random.sample(qas, int(x.group(1)))
                    await message.channel.send(f"Starting game with **{x.group(1)}** questions and category **{x.group(2)}**")
                    GAME_RUNNING = True
                    for i, qa in enumerate(sub_qas):
                        for j in range(4):
                            if not FORCE_QUIT:
                                if j == 0:
                                    await message.channel.send(f"**Question {i+1}**: {qa[0]}")
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
                                        break
                                    if SKIP:
                                        await message.channel.send(f"Correct answer: **{ans}**.")
                                        SKIP = False
                                        break
                                    else:
                                        elapsed = time.time() - start
                                        await message.channel.send(f"Correct answer: **{ans}**.\n**{msg.author}** correctly answered **{msg.content}** in **{elapsed:.2f}** seconds, earning **{5 - j}** points!")
                                        if str(msg.author) in RANKINGS.keys():
                                            RANKINGS[str(msg.author)] += 5 - j
                                        else:
                                            RANKINGS[str(msg.author)] = 5 - j
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
                                    break
                    await message.channel.send("End of game!")
                    ranks = "\n".join([f"{i}. {x[0]}: {x[1]}" for i, x in enumerate(RANKINGS.items())])
                    await message.channel.send(f"__**Rankings**__:\n{ranks}")
                    FORCE_QUIT = False
                    GAME_RUNNING = False
                else:
                    await message.channel.send(f"Not enough questions, max is **{len(qas)}**")
            else:
                l = [f"**{x[0]}**: {x[1]} questions" for x in ZIPPED]
                await message.channel.send(f"Category **{x.group(2)}** not found, valid options are:\n" + "\n".join(l))
    
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
To adjust the **delay between hints**, use **{SYMBOL}hintdelay <seconds>**. Default value is 10.
To adjust the **delay between questions**, **use {SYMBOL}qdelay <seconds>**. Default value is 5.
To **check rankings**, use **{SYMBOL}rankings**.
To **reset rankingas**, use **{SYMBOL}resetrankings**.
To change the bot's **prefix**, **use {SYMBOL}prefix <new_prefix>** Default value is >.
To adjust the **correctness threshold**, **use {SYMBOL}ct <number_between_0_and_100>**. Default value is 80.
To **start a game**, use **{SYMBOL}start questions <number_of_questions> category <category_name>**.
To **skip a question** while a game is running, use **{SYMBOL}skip**,
To **end a game** that is currently running, use **{SYMBOL}stop**.""")
        
client.run(TOKEN)