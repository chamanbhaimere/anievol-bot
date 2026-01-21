import aiohttp
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# API Endpoint
WAIFU_API_URL = "https://api.waifu.im/search"

# Available SFW Tags (Hardcoded for performance, can be fetched dynamically but better as static menu)
SFW_TAGS = [
    "maid", "waifu", "marin-kitagawa", 
    "mori-calliope", "raiden-shogun", "oppai", 
    "selfies", "uniform", "kamisato-ayaka"
]

@Client.on_message(filters.command("waifu") & filters.incoming)
async def get_waifu(client: Client, message: Message):
    """
    Fetch a random anime image from waifu.im
    Usage: /waifu [tag] OR /waifu tags
    """
    args = message.text.split(maxsplit=1)
    
    if len(args) > 1 and args[1].lower() == "tags":
        return await show_tag_menu(message)

    included_tags = []
    if len(args) > 1:
        included_tags = [tag.strip().lower() for tag in args[1].split(",")]

    await fetch_and_send_waifu(message, included_tags)

async def show_tag_menu(message: Message):
    """Show interactive tag selection menu"""
    buttons = []
    row = []
    for tag in SFW_TAGS:
        row.append(InlineKeyboardButton(tag.replace("-", " ").title(), callback_data=f"tagwaifu_{tag}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("🎲 Random Waifu", callback_data="regen_waifu")])
    
    await message.reply_text(
        "<b>🎨 Select a Tag to Generate Image:</b>",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def fetch_and_send_waifu(message: Union[Message, CallbackQuery], included_tags=None, is_callback=False):
    """Helper to fetch and send image"""
    params = {"is_nsfw": "false"}
    if included_tags:
        params["included_tags"] = included_tags

    # If it's a callback, we update the message; if it's a new command, we send a new one
    target = message if not is_callback else message.message
    
    if not is_callback:
        status_msg = await target.reply_text("<b>Generating image... 🎨</b>")
    else:
        await message.answer("Generating...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WAIFU_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if "images" in data and data["images"]:
                        image_info = data["images"][0]
                        image_url = image_info["url"]
                        source_url = image_info.get("source", "https://waifu.im")
                        tags_str = ", ".join([t['name'] for t in image_info['tags']])
                        
                        buttons = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔗 Source", url=source_url)],
                            [InlineKeyboardButton("🔄 Another", callback_data=f"regen_waifu_{included_tags[0] if included_tags else 'random'}")],
                            [InlineKeyboardButton("📂 Tag Menu", callback_data="waifu_tag_menu")]
                        ])

                        caption = f"<b>✨ Random Waifu ✨</b>\n\n<b>Tags:</b> <code>{tags_str}</code>"
                        
                        if is_callback:
                            await message.edit_message_media(
                                media=dict(type="photo", media=image_url, caption=caption),
                                reply_markup=buttons
                            )
                        else:
                            await target.reply_photo(photo=image_url, caption=caption, reply_markup=buttons)
                            await status_msg.delete()
                    else:
                        error_text = "<b>❌ No images found for those tags!</b>"
                        if is_callback: await message.answer(error_text, show_alert=True)
                        else: await status_msg.edit(error_text)
                else:
                    error_text = f"<b>❌ API Error: {response.status}</b>"
                    if is_callback: await message.answer(error_text, show_alert=True)
                    else: await status_msg.edit(error_text)
    except Exception as e:
        logging.error(f"Error fetching waifu: {e}")
        error_text = f"<b>❌ Error:</b> <code>{str(e)}</code>"
        if is_callback: await message.answer(error_text, show_alert=True)
        else: await status_msg.edit(error_text)

@Client.on_callback_query(filters.regex("^regen_waifu_"))
async def regen_waifu_specific_callback(client: Client, query: CallbackQuery):
    tag = query.data.split("_")[-1]
    included_tags = [tag] if tag != "random" else None
    await fetch_and_send_waifu(query, included_tags, is_callback=True)

@Client.on_callback_query(filters.regex("^tagwaifu_"))
async def tag_waifu_callback(client: Client, query: CallbackQuery):
    tag = query.data.split("_")[1]
    await fetch_and_send_waifu(query, [tag], is_callback=True)

@Client.on_callback_query(filters.regex("^waifu_tag_menu$"))
async def waifu_tag_menu_callback(client: Client, query: CallbackQuery):
    """Switch back to tag menu"""
    buttons = []
    row = []
    for tag in SFW_TAGS:
        row.append(InlineKeyboardButton(tag.replace("-", " ").title(), callback_data=f"tagwaifu_{tag}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🎲 Random Waifu", callback_data="regen_waifu_random")])
    
    await query.edit_message_caption(
        caption="<b>🎨 Select a Tag to Generate Image:</b>",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
