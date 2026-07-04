"""
Fayllarni yuklab olish va Telegram kanal/foydalanuvchiga yuborish
Userbot (Telethon) qo'llab-quvvatlash bilan
"""

import os
import re
import math
import logging
import asyncio
import aiohttp
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def make_filename(title: str, quality: str = "", part: int = 0) -> str:
    # Maxsus belgilarni tozalash
    clean = re.sub(r'[^\w\s-]', '', title).strip().replace(" ", "_")
    part_str = f"_part{part}" if part else ""
    qual_str = f"_{quality.replace(' ', '')}" if quality else ""
    return f"{clean}{part_str}{qual_str}.mp4"


def get_file_size_mb(filepath: str) -> float:
    if os.path.exists(filepath):
        return os.path.getsize(filepath) / (1024 * 1024)
    return 0.0


def delete_file(filepath: str):
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        logger.error(f"Delete file error: {e}")


async def download_file(url: str, filename: str, progress_cb=None) -> str:
    """
    HTTP/HTTPS havoladan faylni yuklab oladi va saqlaydi.
    """
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=1800) as resp:
                if resp.status != 200:
                    logger.error(f"Download failed status {resp.status} for {url}")
                    return ""

                total_size = int(resp.headers.get("content-length", 0))
                downloaded = 0

                with open(filepath, "wb") as f:
                    async for chunk in resp.content.iter_chunked(1024 * 512): # 512KB chunks
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0 and progress_cb:
                                pct = (downloaded / total_size) * 100
                                try:
                                    await progress_cb(downloaded, total_size, pct)
                                except Exception:
                                    pass

        return filepath
    except Exception as e:
        logger.error(f"Download exception for {url}: {e}")
        delete_file(filepath)
        return ""


async def upload_to_channel(bot: Bot, channel: str, filepath: str, caption: str):
    """
    Faylni telegram kanaliga yuklaydi (50MB gacha standart Bot API, 50MB+ userbot orqali)
    Returns: (msg_id, file_id) yoki None
    """
    try:
        mb = get_file_size_mb(filepath)

        # Bot API 50MB cheklov
        if mb <= 50.0:
            with open(filepath, "rb") as f:
                msg = await bot.send_document(
                    chat_id=channel,
                    document=f,
                    caption=caption,
                    parse_mode="HTML"
                )
                file_id = msg.document.file_id if msg.document else ""
                return msg.message_id, file_id
        else:
            logger.info(f"File size {mb:.1f}MB exceeds 50MB. Userbot required.")
            return None

    except Exception as e:
        logger.error(f"Upload to channel error: {e}")
        return None


async def forward_from_channel(bot: Bot, channel: str, msg_id: int, user_id: int) -> bool:
    """
    Kanal doirasidagi xabarni foydalanuvchiga forward/copy qiladi
    """
    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=channel,
            message_id=msg_id
        )
        return True
    except Exception as e:
        logger.error(f"Forward from channel error: {e}")
        return False


async def send_by_file_id(bot: Bot, user_id: int, file_id: str, caption: str) -> bool:
    """
    Saqlangan Telegram file_id orqali yuboradi
    """
    try:
        await bot.send_document(
            chat_id=user_id,
            document=file_id,
            caption=caption,
            parse_mode="HTML"
        )
        return True
    except Exception as e:
        logger.error(f"Send by file_id error: {e}")
        return False
