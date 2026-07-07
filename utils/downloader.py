"""
Fayllarni yuklab olish va Telegram kanal/foydalanuvchiga yuborish
Userbot (Telethon) qo'llab-quvvatlash bilan
"""

import os
import re
import math
import time
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


def format_progress_bar(downloaded: int, total: int, speed_bps: float, elapsed_sec: float, stage: str = "⬇️ Yuklab olinmoqda") -> str:
    """
    Chiroyli progress bar va real vaqt statistikasi
    """
    pct = (downloaded / total * 100) if total > 0 else 0.0
    pct = min(100.0, max(0.0, pct))
    filled = int(12 * pct / 100)
    bar = "█" * filled + "░" * (12 - filled)

    dl_mb = downloaded / (1024 * 1024)
    tot_mb = total / (1024 * 1024) if total > 0 else dl_mb

    speed_mbps = speed_bps / (1024 * 1024)
    if speed_mbps >= 1.0:
        speed_str = f"{speed_mbps:.2f} MB/s"
    elif speed_bps > 0:
        speed_str = f"{speed_bps/1024:.1f} KB/s"
    else:
        speed_str = "0 KB/s"

    if speed_bps > 0 and total > downloaded:
        eta_sec = (total - downloaded) / speed_bps
        eta_m, eta_s = divmod(int(eta_sec), 60)
        eta_str = f"{eta_m:02d}:{eta_s:02d}"
    else:
        eta_str = "--:--"

    spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    spin = spinners[int(elapsed_sec * 2) % len(spinners)]

    return (
        f"{spin} <b>{stage}:</b> {pct:.1f}%\n"
        f"<code>[{bar}]</code>\n"
        f"📦 <b>Hajmi:</b> {dl_mb:.1f} / {tot_mb:.1f} MB\n"
        f"⚡️ <b>Tezlik:</b> {speed_str} | ⏱ <b>Qolgan vaqt:</b> {eta_str}"
    )


async def download_file(url: str, filename: str, progress_cb=None) -> str:
    """
    HTTP/HTTPS havoladan faylni yuklab oladi va saqlaydi. Real vaqtdagi tezlik va progress bilan.
    """
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        referer = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Referer": referer,
            "Connection": "keep-alive",
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=1800) as resp:
                if resp.status != 200:
                    logger.error(f"Download failed status {resp.status} for {url}")
                    return ""

                total_size = int(resp.headers.get("content-length", 0))
                downloaded = 0
                start_time = time.time()
                last_time = start_time
                last_downloaded = 0

                # Biz yuklashni bloklamaslik uchun, progress yangilashni alohida task qilib fonda ishlatamiz.
                # Bu orqali aiohttp eng yuqori tezlikda (bloklanmasdan) faylni yuklab oladi.
                async def progress_reporter():
                    nonlocal last_time, last_downloaded
                    while downloaded < total_size:
                        try:
                            await asyncio.sleep(3.0)  # Har 3 soniyada xabar yuborish
                            now = time.time()
                            dt = now - last_time
                            if dt > 0:
                                speed_bps = (downloaded - last_downloaded) / dt
                                elapsed = now - start_time
                                pct = (downloaded / total_size * 100) if total_size > 0 else 0

                                last_time = now
                                last_downloaded = downloaded

                                if progress_cb:
                                    await progress_cb(downloaded, total_size, pct, speed_bps, elapsed)
                        except asyncio.CancelledError:
                            break
                        except Exception:
                            pass

                reporter_task = None
                if progress_cb and total_size > 0:
                    reporter_task = asyncio.create_task(progress_reporter())

                loop = asyncio.get_running_loop()
                try:
                    with open(filepath, "wb") as f:
                        async for chunk in resp.content.iter_chunked(256 * 1024):  # 256KB chunks for steady streaming and accurate progress
                            if chunk:
                                await loop.run_in_executor(None, f.write, chunk)
                                downloaded += len(chunk)
                finally:
                    if reporter_task:
                        reporter_task.cancel()
                        try:
                            await reporter_task
                        except Exception:
                            pass

                # Yakuniy holatni yangilash
                if progress_cb:
                    try:
                        now = time.time()
                        elapsed = now - start_time
                        await progress_cb(total_size, total_size, 100.0, 0, elapsed)
                    except Exception:
                        pass

        return filepath
    except Exception as e:
        logger.error(f"Download exception for {url}: {e}")
        delete_file(filepath)
        return ""


async def upload_to_channel(bot: Bot, channel: str, filepath: str, caption: str):
    """
    Faylni telegram kanaliga yuklaydi (50MB gacha standart Bot API)
    Returns: (msg_id, file_id) yoki None
    """
    try:
        mb = get_file_size_mb(filepath)

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

