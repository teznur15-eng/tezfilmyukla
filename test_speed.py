import asyncio
import time
import os
import sys

# Project root path setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.downloader import download_file

async def main():
    # Cloudflare speed test 50MB file URL
    url = "https://speed.cloudflare.com/__down?bytes=52428800"
    filename = "test_speed_50mb.bin"
    
    print("\n🚀 Python virtual muhitida yuklash tezligini tekshiramiz...")
    print(f"Manzil: {url}")
    print("----------------------------------------------------------------")
    
    async def progress(downloaded, total, pct, speed_bps, elapsed):
        speed_mbs = speed_bps / (1024 * 1024)        # MegaBytes per second
        print(f"📊 {pct:.1f}% | Yuklandi: {downloaded / (1024*1024):.1f}MB / {total / (1024*1024):.1f}MB | "
              f"⚡️ Tezlik: {speed_mbs:.2f} MB/s", end="\r")

    start = time.time()
    filepath = await download_file(url, filename, progress_cb=progress)
    end = time.time()
    print() # New line after \r progress
    
    if filepath and os.path.exists(filepath):
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        duration = end - start
        avg_speed = size_mb / duration if duration > 0 else 0
        print("----------------------------------------------------------------")
        print(f"✅ TEST MUVAFFAQIYATLI YAKUNLANDI!")
        print(f"📁 Yuklangan fayl: {filepath}")
        print(f"📦 Fayl hajmi: {size_mb:.2f} MB")
        print(f"⏱ Jami ketgan vaqt: {duration:.2f} soniya")
        print(f"🚀 O'rtacha yuklash tezligi: {avg_speed:.2f} MB/s ({avg_speed * 8:.2f} Mbps)")
        
        # Clean up
        try:
            os.remove(filepath)
            print("🧹 Test fayli o'chirildi.")
        except Exception:
            pass
    else:
        print("❌ Fayl yuklashda xatolik yuz berdi!")

if __name__ == "__main__":
    asyncio.run(main())
