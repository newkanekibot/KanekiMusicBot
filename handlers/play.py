import os
import ffmpeg
import aiohttp
import aiofiles
import requests
import converter
from Python_ARQ import ARQ
from asyncio.queues import QueueEmpty
from pyrogram import Client, filters
from typing import Callable
from callsmusic import callsmusic, queues
from helpers.admins import get_administrators
from youtube_search import YoutubeSearch
from callsmusic.callsmusic import client as USER
from pyrogram.errors import UserAlreadyParticipant
from downloaders import youtube

from config import que, DURATION_LIMIT, BOT_USERNAME
from helpers.filters import command, other_filters
from helpers.decorators import authorized_users_only
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from cache.admins import admins as a
from PIL import Image, ImageFont, ImageDraw
chat_id = None

ARQ_API_KEY = "UOXSNM-EDTSYU-YIYJOI-BMCROR-ARQ"
aiohttpsession = aiohttp.ClientSession()
arq = ARQ("https://thearq.tech", ARQ_API_KEY, aiohttpsession)

chat_id = None
DISABLED_GROUPS = []
useer = "NaN"

def cb_admin_check(func: Callable) -> Callable:
    async def decorator(client, cb):
        admemes = a.get(cb.message.chat.id)
        if cb.from_user.id in admemes:
            return await func(client, cb)
        await cb.answer("Anda tidak diizinkan!", show_alert=True)
        return
    return decorator                                                                       
                                          
                                                                                    
def transcode(filename):
    ffmpeg.input(filename).output("input.raw", format="s16le", acodec="pcm_s16le", ac=2, ar="48k").overwrite_output().run() 
    os.remove(filename)

# Convert seconds to mm:ss
def convert_seconds(seconds):
    seconds = seconds % (24 * 3600)
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%02d:%02d" % (minutes, seconds)


# Convert hh:mm:ss to seconds
def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(stringt.split(":"))))


# Change image size
def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    return image.resize((newWidth, newHeight))


async def generate_cover(requested_by, title, views, duration, thumbnail):
    async with aiohttp.ClientSession() as session:
        async with session.get(thumbnail) as resp:
            if resp.status == 200:
                f = await aiofiles.open("background.png", mode="wb")
                await f.write(await resp.read())
                await f.close()
    image1 = Image.open("./background.png")
    image2 = Image.open("etc/foreground.png")
    image3 = changeImageSize(1280, 720, image1)
    image4 = changeImageSize(1280, 720, image2)
    image5 = image3.convert("RGBA")
    image6 = image4.convert("RGBA")
    Image.alpha_composite(image5, image6).save("temp.png")
    img = Image.open("temp.png")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("etc/font.otf", 32)
    draw.text((205, 550), f"Judul: {title}", (51, 215, 255), font=font)
    draw.text(
        (205, 590), f"Durasi: {duration}", (255, 255, 255), font=font
    )
    draw.text((205, 630), f"Views: {views}", (255, 255, 255), font=font)
    draw.text((205, 670),
        f"Atas permintaan: {requested_by}",
        (255, 255, 255),
        font=font,
    )
    img.save("final.png")
    os.remove("temp.png")
    os.remove("background.png")


@Client.on_message(command(["playlist", f"playlist@{BOT_USERNAME}"]) & filters.group & ~filters.edited)
async def playlist(client, message):
    global que
    queue = que.get(message.chat.id)
    if not queue:
        await message.reply_text("**Sedang tidak memutar lagu!**")
    temp = [t for t in queue]
    now_playing = temp[0][0]
    by = temp[0][1].mention(style="md")
    msg = "**Lagu Yang Sedang dimainkan** di {}".format(message.chat.title)
    msg += "\n• "+ now_playing
    msg += "\n• Atas permintaan "+by
    temp.pop(0)
    if temp:
        msg += "\n\n"
        msg += "**Antrian Lagu**"
        for song in temp:
            name = song[0]
            usr = song[1].mention(style="md")
            msg += f"\n• {name}"
            msg += f"\n• Atas permintaan {usr}\n"
    await message.reply_text(msg)


# ============================= Settings =========================================
def updated_stats(chat, queue, vol=100):
    if chat.id in callsmusic.pytgcalls.active_calls:
        stats = "Pengaturan dari **{}**".format(chat.title)
        if len(que) > 0:
            stats += "\n\n"
            stats += "Volume: {}%\n".format(vol)
            stats += "Lagu dalam antrian: `{}`\n".format(len(que))
            stats += "Sedang memutar lagu: **{}**\n".format(queue[0][0])
            stats += "Atas permintaan: {}".format(queue[0][1].mention)
    else:
        stats = None
    return stats


def r_ply(type_):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏹", "leave"),
                InlineKeyboardButton("⏸", "puse"),
                InlineKeyboardButton("▶️", "resume"),
                InlineKeyboardButton("⏭", "skip")
            ],
            [
                InlineKeyboardButton("📖 Daftar Putar", "playlist"),
            ],
            [       
                InlineKeyboardButton("🗑 Tutup", "cls")
            ]        
        ]
    )


@Client.on_message(command(["current", f"current@{BOT_USERNAME}"]) & filters.group & ~filters.edited)
async def ee(client, message):
    queue = que.get(message.chat.id)
    stats = updated_stats(message.chat, queue)
    if stats:
        await message.reply(stats)              
    else:
        await message.reply("**Silahkan Nyalakan dulu VCG nya!**")


@Client.on_message(command(["player", f"player@{BOT_USERNAME}"]) & filters.group & ~filters.edited)
@authorized_users_only
async def settings(client, message):
    playing = None
    if message.chat.id in callsmusic.pytgcalls.active_calls:
        playing = True
    queue = que.get(message.chat.id)
    stats = updated_stats(message.chat, queue)
    if stats:
        if playing:
            await message.reply(stats, reply_markup=r_ply("pause"))
            
        else:
            await message.reply(stats, reply_markup=r_ply("play"))
    else:
        await message.reply("**Silahkan Nyalakan dulu VCG nya!**")


@Client.on_callback_query(filters.regex(pattern=r"^(playlist)$"))
async def p_cb(b, cb):
    global que
    qeue = que.get(cb.message.chat.id)
    type_ = cb.matches[0].group(1)
    chat_id = cb.message.chat.id
    m_chat = cb.message.chat
    the_data = cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "playlist":       
        queue = que.get(cb.message.chat.id)
        if not queue:   
            await cb.message.edit("**Sedang tidak memutar lagu!**")
        temp = [t for t in queue]
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "**Lagu Yang Sedang dimainkan** di {}".format(cb.message.chat.title)
        msg += "\n• "+ now_playing
        msg += "\n• Atas permintaan "+by
        temp.pop(0)
        if temp:
             msg += "\n\n"
             msg += "**Antrian Lagu**"
             for song in temp:
                 name = song[0]
                 usr = song[1].mention(style="md")
                 msg += f"\n• {name}"
                 msg += f"\n• Atas permintaan {usr}\n"
        await cb.message.edit(msg)      


@Client.on_callback_query(filters.regex(pattern=r"^(play|pause|skip|leave|puse|resume|menu|cls)$"))
@cb_admin_check
async def m_cb(b, cb):
    global que
    qeue = que.get(cb.message.chat.id)
    type_ = cb.matches[0].group(1)
    chat_id = cb.message.chat.id
    m_chat = cb.message.chat

    the_data = cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "pause":
        if (
            chat_id not in callsmusic.pytgcalls.active_calls
                ) or (
                    callsmusic.pytgcalls.active_calls[chat_id] == "paused"
                ):
            await cb.answer("Assistant Sedang Tidak Terhubung dengan VCG!", show_alert=True)
        else:
            callsmusic.pytgcalls.pause_stream(chat_id)

            await cb.answer("Music Paused!")
            await cb.message.edit(updated_stats(m_chat, qeue), reply_markup=r_ply("play"))

    elif type_ == "play":       
        if (
            chat_id not in callsmusic.pytgcalls.active_calls
            ) or (
                callsmusic.pytgcalls.active_calls[chat_id] == "playing"
            ):
                await cb.answer("Assistant Sedang Tidak Terhubung dengan VCG!", show_alert=True)
        else:
            callsmusic.pytgcalls.resume_stream(chat_id)
            await cb.answer("Music Resumed!")
            await cb.message.edit(updated_stats(m_chat, qeue), reply_markup=r_ply("pause"))

    elif type_ == "playlist":
        queue = que.get(cb.message.chat.id)
        if not queue:   
            await cb.message.edit("Sedang tidak memutar lagu")
        temp = [t for t in queue]
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "**Lagu Yang Sedang dimainkan** di {}".format(cb.message.chat.title)
        msg += "\n• "+ now_playing
        msg += "\n• Atas permintaan "+by
        temp.pop(0)
        if temp:
             msg += "\n\n"
             msg += "**Antrian Lagu**"
             for song in temp:
                 name = song[0]
                 usr = song[1].mention(style="md")
                 msg += f"\n• {name}"
                 msg += f"\n• Atas permintaan {usr}\n"
        await cb.message.edit(msg)      

    elif type_ == "resume":     
        if (
            chat_id not in callsmusic.pytgcalls.active_calls
            ) or (
                callsmusic.pytgcalls.active_calls[chat_id] == "playing"
            ):
                await cb.answer("Obrolan tidak terhubung atau sudah dimainkan", show_alert=True)
        else:
            callsmusic.pytgcalls.resume_stream(chat_id)
            await cb.answer("Music Resumed!")

    elif type_ == "puse":         
        if (
            chat_id not in callsmusic.pytgcalls.active_calls
                ) or (
                    callsmusic.pytgcalls.active_calls[chat_id] == "paused"
                ):
            await cb.answer("Obrolan tidak terhubung atau sudah di pause", show_alert=True)
        else:
            callsmusic.pytgcalls.pause_stream(chat_id)

            await cb.answer("Music Paused!")

    elif type_ == "cls":          
        await cb.answer("Closed menu")
        await cb.message.delete()       

    elif type_ == "menu":  
        stats = updated_stats(cb.message.chat, qeue)  
        await cb.answer("Menu opened")
        marr = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏹", "leave"),
                    InlineKeyboardButton("⏸", "puse"),
                    InlineKeyboardButton("▶️", "resume"),
                    InlineKeyboardButton("⏭", "skip")

                ],
                [
                    InlineKeyboardButton("📖 Daftar Putar", "playlist"),

                ],
                [       
                    InlineKeyboardButton("🗑 Tutup", "cls")
                ]        
            ]
        )
        await cb.message.edit(stats, reply_markup=marr)

    elif type_ == "skip":        
        if qeue:
            skip = qeue.pop(0)
        if chat_id not in callsmusic.pytgcalls.active_calls:
            await cb.answer("Assistant Sedang Tidak Terhubung dengan VCG!", show_alert=True)
        else:
            callsmusic.queues.task_done(chat_id)

            if callsmusic.queues.is_empty(chat_id):
                callsmusic.pytgcalls.leave_group_call(chat_id)

                await cb.message.edit("• Tidak Ada Lagi Daftar Putar.\n• Meninggalkan VCG!")
            else:
                callsmusic.pytgcalls.change_stream(
                    chat_id,
                    callsmusic.queues.get(chat_id)["file"]
                )
                await cb.answer("Skipped")
                await cb.message.edit(f"• Skipped **{skip[0]}**\n• Now Playing **{qeue[0][0]}**")

    elif type_ == "leave":
        if chat_id in callsmusic.pytgcalls.active_calls:
            try:
                callsmusic.queues.clear(chat_id)
            except QueueEmpty:
                pass

            callsmusic.pytgcalls.leave_group_call(chat_id)
            await cb.message.edit("❌ **Memberhentikan Lagu!**")
        else:
            await cb.answer("Assistant Sedang Tidak Terhubung dengan VCG!", show_alert=True)


@Client.on_message(command("play") & other_filters)
async def play(_, message: Message):
    global que
    global useer
    if message.chat.id in DISABLED_GROUPS:
        return    
    lel = await message.reply("🔄 **processing...**")
    administrators = await get_administrators(message.chat)
    chid = message.chat.id
    try:
        user = await USER.get_me()
    except:
        user.first_name = "helper"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await _.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message.from_user.id:
                if message.chat.title.startswith("Channel Music: "):
                    await lel.edit(
                        f"<b>please add {user.first_name} to your channel.</b>",
                    )
                    pass
                try:
                    invitelink = await _.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "<b>make me as admin first.</b>",
                    )
                    return
                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message(
                        message.chat.id, "👻: i'm joined to this group for playing music on voice chat"
                    )
                    await lel.edit(
                        "<b>helper userbot joined your chat</b>",
                    )
                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b>⛑ Flood Wait Error ⛑\n{user.first_name} tidak dapat bergabung dengan grup Anda karena banyaknya permintaan bergabung untuk userbot! Pastikan pengguna tidak dibanned dalam grup."
                        f"\n\nAtau tambahkan @{ASSISTANT_NAME} secara manual ke Grup Anda dan coba lagi</b>",
                    )
    try:
        await USER.get_chat(chid)
        # lmoa = await client.get_chat_member(chid,wew)
    except:
        await lel.edit(
            f"<i>{user.first_name} was banned in this group, ask admin to unban @{ASSISTANT_NAME} manually.</i>"
        )
        return
    text_links=None
    await lel.edit("🔎 **finding song...**")
    if message.reply_to_message:
        entities = []
        toxt = message.reply_to_message.text or message.reply_to_message.caption
        if message.reply_to_message.entities:
            entities = message.reply_to_message.entities + entities
        elif message.reply_to_message.caption_entities:
            entities = message.reply_to_message.entities + entities
        urls = [entity for entity in entities if entity.type == 'url']
        text_links = [
            entity for entity in entities if entity.type == 'text_link'
        ]
    else:
        urls=None
    if text_links:
        urls = True
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    rpk = "[" + user_name + "](tg://user?id=" + str(user_id) + ")"
    audio = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )
    if audio:
        if round(audio.duration / 60) > DURATION_LIMIT:
            raise DurationLimitError(
                f"❌ **lagu dengan durasi lebih dari** `{DURATION_LIMIT}` **menit tidak dapat diputar!**"
            )
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏺️ ᴍᴇɴᴜ", callback_data="menu"),
                    InlineKeyboardButton("🗑️ ᴄʟᴏꜱᴇ", callback_data="cls"),
                ],[
                    InlineKeyboardButton("⚙️ ᴄʜᴀɴɴᴇʟ", url=f"https://t.me/{UPDATES_CHANNEL}")
                ],
            ]
        )
        file_name = get_file_name(audio)
        title = file_name
        thumb_name = "https://telegra.ph/file/02cebeab88892fe92071f.png"
        thumbnail = thumb_name
        duration = round(audio.duration / 60)
        views = "Locally added"
        message.from_user.first_name
        await generate_cover(requested_by, title, views, duration, thumbnail)
        file_path = await converter.convert(
            (await message.reply_to_message.download(file_name))
            if not path.isfile(path.join("downloads", file_name))
            else file_name
        )
    elif urls:
        query = toxt
        await lel.edit("🎵 **processing song...**")
        ydl_opts = {"format": "bestaudio[ext=m4a]"}
        try:
            results = YoutubeSearch(query, max_results=1).to_dict()
            url = f"https://youtube.com{results[0]['url_suffix']}"
            # print(results)
            title = results[0]["title"][:65]
            thumbnail = results[0]["thumbnails"][0]
            thumb_name = f"thumb{title}.jpg"
            thumb = requests.get(thumbnail, allow_redirects=True)
            open(thumb_name, "wb").write(thumb.content)
            duration = results[0]["duration"]
            results[0]["url_suffix"]
            views = results[0]["views"]
        except Exception as e:
            await lel.edit(
                "**❌ song not found.** please give a valid song name."
            )
            print(str(e))
            return
        dlurl=url
        dlurl=dlurl.replace("youtube","youtubepp")
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏺️ ᴍᴇɴᴜ", callback_data="menu"),
                    InlineKeyboardButton("🗑️ ᴄʟᴏꜱᴇ", callback_data="cls"),
                ],[
                    InlineKeyboardButton("⚙️ ᴄʜᴀɴɴᴇʟ", url=f"https://t.me/{UPDATES_CHANNEL}")
                ],
            ]
        )
        requested_by = message.from_user.first_name
        await generate_cover(requested_by, title, views, duration, thumbnail)
        file_path = await converter.convert(youtube.download(url))        
    else:
        query = ""
        for i in message.command[1:]:
            query += " " + str(i)
        print(query)
        await lel.edit("🎵 **processing song...**")
        ydl_opts = {"format": "bestaudio[ext=m4a]"}
        
        try:
          results = YoutubeSearch(query, max_results=6).to_dict()
        except:
          await lel.edit("**anda tidak memberikan judul lagu apapun !**")
        # veez project
        try:
            toxxt = "__pilih lagu untuk dimainkan:__\n\n"
            j = 0
            useer=user_name
            emojilist = ["❶","❷","❸","❹","❺","❻"]
            while j < 6:
                toxxt += f"{emojilist[j]} [{results[j]['title'][:35]}...](https://youtube.com{results[j]['url_suffix']})\n"
                toxxt += f" ├ <b>Duration</b>- {results[j]['duration']}\n"
                toxxt += f" ├ <b>Views</b> - {results[j]['views']}\n"
                j += 1            
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("❶", callback_data=f'plll 0|{query}|{user_id}'),
                        InlineKeyboardButton("❷", callback_data=f'plll 1|{query}|{user_id}'),
                        InlineKeyboardButton("❸", callback_data=f'plll 2|{query}|{user_id}'),
                    ],
                    [
                        InlineKeyboardButton("❹", callback_data=f'plll 3|{query}|{user_id}'),
                        InlineKeyboardButton("❺", callback_data=f'plll 4|{query}|{user_id}'),
                    ],
                    [
                        InlineKeyboardButton("❻", callback_data=f'plll 5|{query}|{user_id}'),
                    ],
                    [InlineKeyboardButton(text="🗑 Close", callback_data="cls")],
                ]
            )



            await message.reply_photo(
                photo=f"{THUMB_IMG}",
                caption=toxxt,
                reply_markup=keyboard
            )

            await lel.delete()
            # veez project
            return
            # veez project
        except:
            await lel.edit("__no more results, starting to playing...__")
                        
            # print(results)
            try:
                url = f"https://youtube.com{results[0]['url_suffix']}"
                title = results[0]["title"][:65]
                thumbnail = results[0]["thumbnails"][0]
                thumb_name = f"thumb-{title}.jpg"
                thumb = requests.get(thumbnail, allow_redirects=True)
                open(thumb_name, "wb").write(thumb.content)
                duration = results[0]["duration"]
                results[0]["url_suffix"]
                views = results[0]["views"]
            except Exception as e:
                await lel.edit(
                "**❌ song not found.** please give a valid song name."
            )
                print(str(e))
                return
            dlurl=url
            dlurl=dlurl.replace("youtube","youtubepp")
            keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏺️ ᴍᴇɴᴜ", callback_data="menu"),
                    InlineKeyboardButton("🗑️ ᴄʟᴏꜱᴇ", callback_data="cls"),
                ],[
                    InlineKeyboardButton("⚙️ ᴄʜᴀɴɴᴇʟ", url=f"https://t.me/{UPDATES_CHANNEL}")
                ],
            ]
            )
            message.from_user.first_name
            await generate_cover(requested_by, title, views, duration, thumbnail)
            file_path = await converter.convert(youtube.download(url))   
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.pytgcalls.active_calls:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await message.reply_photo(
            photo="final.png",
            caption=f"🔖 **Judul:** [{title[:65]}]({url})\n⏱ **Durasi:** {duration}\n💡 **Status:** Antrian Ke `{position}`\n" \
                   +f"🌹 **Permintaan:** {message.from_user.mention}",
            reply_markup=keyboard
        )
    else:
        chat_id = get_chat_id(message.chat)
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        try:
            callsmusic.pytgcalls.join_group_call(chat_id, file_path)
        except:
            message.reply("**voice chat group tidak aktif, tidak dapat memutar lagu.**")
            return
        await message.reply_photo(
            photo="final.png",
            caption=f"🔖 **Judul:** [{title[:65]}]({url})\n⏱ **Durasi:** {duration}\n💡 **Status:** `Sedang Memutar`\n" \
                   +f"🌹 **Permintaan:** {message.from_user.mention}",
            reply_markup=keyboard
        )
        os.remove("final.png")
        return await lel.delete()
@Client.on_callback_query(filters.regex(pattern=r"plll"))
async def lol_cb(b, cb):
    global que
    cbd = cb.data.strip()
    chat_id = cb.message.chat.id
    typed_=cbd.split(None, 1)[1]
    try:
        x,query,useer_id = typed_.split("|")      
    except:
        await cb.message.edit("❌ song not found")
        return
    useer_id = int(useer_id)
    if cb.from_user.id != useer_id:
        await cb.answer("anda bukan orang yang meminta untuk memutar lagu ini!", show_alert=True)
        return
    await cb.message.edit("🔁**Menghubungkan...**")
    x=int(x)
    try:
        cb.message.reply_to_message.from_user.first_name
    except:
        cb.message.from_user.first_name
    results = YoutubeSearch(query, max_results=6).to_dict()
    resultss=results[x]["url_suffix"]
    title=results[x]["title"][:65]
    thumbnail=results[x]["thumbnails"][0]
    duration=results[x]["duration"]
    views=results[x]["views"]
    url = f"https://www.youtube.com{resultss}"
    try:    
        secmul, dur, dur_arr = 1, 0, duration.split(":")
        for i in range(len(dur_arr)-1, -1, -1):
            dur += (int(dur_arr[i]) * secmul)
            secmul *= 60
        if (dur / 60) > DURATION_LIMIT:
             await cb.message.edit(f"❌ Lagu dengan durasi lebih dari `{DURATION_LIMIT}` menit tidak dapat diputar.")
             return
    except:
        pass
    try:
        thumb_name = f"thumb{title}.jpg"
        thumb = requests.get(thumbnail, allow_redirects=True)
        open(thumb_name, "wb").write(thumb.content)
    except Exception as e:
        print(e)
        return
    dlurl=url
    dlurl=dlurl.replace("youtube", "youtubepp")
    keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏺️ ᴍᴇɴᴜ", callback_data="menu"),
                    InlineKeyboardButton("🗑️ ᴄʟᴏꜱᴇ", callback_data="cls"),
                ],[
                    InlineKeyboardButton("⚙️ ᴄʜᴀɴɴᴇʟ", url=f"https://t.me/{UPDATES_CHANNEL}")
                ],
            ]
    )
    requested_by = useer_name
    await generate_cover(requested_by, title, views, duration, thumbnail)
    file_path = await converter.convert(youtube.download(url))  
    if chat_id in callsmusic.pytgcalls.active_calls:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        try:
            r_by = cb.message.reply_to_message.from_user
        except:
            r_by = cb.message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await cb.message.delete()
        await b.send_photo(chat_id,
        photo="final.png",
        caption=f"🔖 **Judul:** [{title[:35]}]({url})\n⏱ **Durasi:** {duration}\n💡 **Status:** Antrian Ke `{position}`\n" \
               +f"🌹 **Permintaan:** {r_by.mention}",
        reply_markup=keyboard,
        )
        os.remove("final.png")
    else:
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        try:
            r_by = cb.message.reply_to_message.from_user
        except:
            r_by = cb.message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        callsmusic.pytgcalls.join_group_call(chat_id, file_path)
        await cb.message.delete()
        await b.send_photo(chat_id,
        photo="final.png",
        caption=f"🔖 **Judul:** [{title[:65]}]({url})\n⏱ **Durasi:** {duration}\n💡 **Status:** `Sedang Memutar`\n" \
               +f"🌹 **Permintaan:** {r_by.mention}",
        reply_markup=keyboard,
        )
        os.remove("final.png")
