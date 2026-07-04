"""
Movie Web Scraper Moduli
Asilmedia, Uzmovie, Uzmovi.tv, Kinolar.tv, Tarjima-kinolar va umumiy internet qidiruvi uchun scraper.
"""

import re
import asyncio
import logging
import urllib.parse
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8,en-US;q=0.7,en;q=0.6"
}


class DownloadLink:
    def __init__(self, url: str, quality: str = "720p HD", part: int = 0, size: str = ""):
        self.url = url
        self.quality = quality
        self.part = part
        self.size = size

    def display_label(self) -> str:
        res = self.quality or "Yuklab olish"
        if self.part:
            res = f"{self.part}-qism ({res})"
        return res


class MovieInfo:
    def __init__(
        self,
        title: str,
        year: str = "",
        quality: str = "",
        language: str = "O'zbek tili",
        genre: str = "",
        description: str = "",
        poster_url: str = "",
        links: list[DownloadLink] = None
    ):
        self.title = title
        self.year = year
        self.quality = quality
        self.language = language
        self.genre = genre
        self.description = description
        self.poster_url = poster_url
        self.links = links or []

    def has_parts(self) -> bool:
        parts = {l.part for l in self.links if l.part > 0}
        return len(parts) > 1 or (len(parts) == 1 and 0 not in parts)

    def get_parts(self) -> list[int]:
        parts = {l.part for l in self.links if l.part > 0}
        return sorted(list(parts))

    def get_links_for_part(self, part: int) -> list[DownloadLink]:
        return [l for l in self.links if l.part == part]


async def scrape_movie(url: str) -> MovieInfo:
    """
    Kino sahifasidan ma'lumotlar va yuklab olish havolalarini ajratib oladi.
    """
    try:
        # To'g'ridan-to'g'ri MP4 / MKV havola bo'lsa
        if any(url.lower().endswith(ext) for ext in [".mp4", ".mkv", ".avi", ".mov"]):
            filename = url.split("/")[-1].split("?")[0]
            clean_title = re.sub(r"[._-]", " ", filename).replace(".mp4", "").replace(".mkv", "").title()
            return MovieInfo(
                title=clean_title or "Video fayl",
                quality="HD",
                links=[DownloadLink(url=url, quality="To'g'ridan to'g'ri MP4", part=0)]
            )

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url, timeout=12, allow_redirects=True) as resp:
                if resp.status != 200:
                    return None
                html_text = await resp.text()

        soup = BeautifulSoup(html_text, "html.parser")

        # Sarlavha
        title_el = soup.select_one("h1, .movie-header h1, .story-title, .short-title, title")
        title = title_el.get_text(strip=True) if title_el else "Kino"
        title = re.sub(r"\s*(watch online|tas-ix|tasix|skachat|yuklab olish|skachat|- Asilmedia|- Uzmovi|- Kinolar)\b", "", title, flags=re.IGNORECASE).strip()

        # Yil
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", title + " " + html_text[:1200])
        year = year_match.group(1) if year_match else ""

        # Poster
        poster_url = ""
        img_el = soup.select_one(".poster img, .movie-poster img, .full-story img, .story-img img, article img, .shortstory img")
        if img_el and img_el.get("src"):
            poster_url = img_el["src"]
            if not poster_url.startswith("http"):
                parsed = urllib.parse.urlparse(url)
                poster_url = f"{parsed.scheme}://{parsed.netloc}{poster_url}"

        # Tavsif
        desc_el = soup.select_one(".description, .full-text, .story-text, #story, .movie-desc, .fstory-post")
        description = desc_el.get_text(strip=True)[:450] if desc_el else ""

        # Sifat
        quality = "720p HD"
        if "1080" in html_text or "FHD" in html_text:
            quality = "1080p Full HD"
        elif "480" in html_text:
            quality = "480p SD"

        links: list[DownloadLink] = []

        # Download / Video selectorlar
        selectors = [
            "a[href*='.mp4']", "a[href*='.mkv']", "a.download-btn", ".down-file a",
            "a[href*='/download/']", "a[href*='download']", ".download-link a", ".file-down a"
        ]
        download_elements = soup.select(", ".join(selectors))

        for el in download_elements:
            href = el.get("href")
            if not href or href.startswith("javascript:") or href == "#":
                continue

            if not href.startswith("http"):
                parsed = urllib.parse.urlparse(url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"

            txt = el.get_text(strip=True)
            q_label = "720p HD"
            if "1080" in txt or "1080" in href:
                q_label = "1080p Full HD"
            elif "480" in txt or "480" in href:
                q_label = "480p SD"
            elif "360" in txt or "360" in href:
                q_label = "360p"
            elif txt and len(txt) < 30:
                q_label = txt

            # Qism
            part = 0
            part_match = re.search(r"(\d+)[-_\s]*(qism|part|seriya|ep)", txt.lower() + " " + href.lower())
            if part_match:
                part = int(part_match.group(1))

            if not any(l.url == href for l in links):
                links.append(DownloadLink(url=href, quality=q_label, part=part, size="Standart"))

        # Embed / Iframe / Source video parser
        if not links:
            for s in soup.find_all(["source", "iframe", "video"]):
                src = s.get("src") or s.get("href")
                if src and any(ext in src.lower() for ext in [".mp4", ".mkv", ".avi", "player", "stream"]):
                    if not src.startswith("http"):
                        parsed = urllib.parse.urlparse(url)
                        src = f"{parsed.scheme}://{parsed.netloc}{src}"
                    links.append(DownloadLink(url=src, quality="720p HD", part=0, size="Standart"))

        # Fallback
        if not links:
            links.append(DownloadLink(url=url, quality="Standart Sifat", part=0, size="Standart"))

        return MovieInfo(
            title=title,
            year=year,
            quality=quality,
            language="O'zbek tili",
            genre="Kino",
            description=description,
            poster_url=poster_url,
            links=links
        )

    except Exception as e:
        logger.error(f"Scrape movie error for {url}: {e}")
        return None


async def search_movies(query: str) -> list[dict]:
    """
    Asilmedia, Uzmovi, Kinolar, Moviy, Tarjima-kinolar saytlarida parallel qidiruv o'tkazadi
    """
    results = []
    query = query.strip()
    if not query:
        return results

    q_enc = urllib.parse.quote(query)

    sites = [
        ("Asilmedia", f"https://asilmedia.net/index.php?do=search&subaction=search&story={q_enc}"),
        ("Uzmovi", f"https://uzmovi.com/search?q={q_enc}"),
        ("Kinolar.tv", f"https://kinolar.tv/?do=search&subaction=search&story={q_enc}"),
        ("Uzfilm", f"https://uzfilm.biz/index.php?do=search&subaction=search&story={q_enc}")
    ]

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tasks = []
        for name, url in sites:
            tasks.append(_search_single_site(session, name, url))

        site_results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in site_results:
            if isinstance(res, list):
                for item in res:
                    if not any(r["url"] == item["url"] for r in results):
                        results.append(item)

    # Agar kam natija bo'lsa, internet qidiruvi
    if len(results) < 3:
        net_res = await internet_search_movie(query)
        for item in net_res:
            if not any(r["url"] == item["url"] for r in results):
                results.append(item)

    return results


async def _search_single_site(session: aiohttp.ClientSession, source_name: str, search_url: str) -> list[dict]:
    items_out = []
    try:
        async with session.get(search_url, timeout=7) as resp:
            if resp.status == 200:
                html_text = await resp.text()
                soup = BeautifulSoup(html_text, "html.parser")
                items = soup.select(".shortstory, .movie-item, article.story, .post-item, .short-story")
                for item in items[:6]:
                    title_el = item.select_one(".title, h2, .short-title, a.story-title, a")
                    link_el = item.select_one("a[href]")
                    img_el = item.select_one("img")

                    if title_el and link_el:
                        title = title_el.get_text(strip=True)
                        movie_url = link_el["href"]
                        poster = img_el["src"] if img_el and "src" in img_el.attrs else ""

                        if movie_url and not movie_url.startswith("http"):
                            parsed = urllib.parse.urlparse(search_url)
                            movie_url = f"{parsed.scheme}://{parsed.netloc}{movie_url}"

                        if movie_url and "search" not in movie_url:
                            items_out.append({
                                "title": title,
                                "url": movie_url,
                                "source": source_name,
                                "year": "",
                                "poster": poster
                            })
    except Exception as e:
        logger.error(f"Search site {source_name} error: {e}")

    return items_out


async def internet_search_movie(query: str) -> list[dict]:
    """
    DuckDuckGo va umumiy web motorlar orqali uzbek kinolarni qidiradi
    """
    results = []
    try:
        q_str = f"{query} o`zbekcha kino tasix mp4"
        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q_str)}"
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(search_url, timeout=8) as resp:
                if resp.status == 200:
                    html_text = await resp.text()
                    soup = BeautifulSoup(html_text, "html.parser")
                    for a in soup.select("a.result__url")[:8]:
                        href = a.get("href")
                        title = a.get_text(strip=True)
                        if href and href.startswith("http") and not any(block in href for block in ["youtube.com", "facebook.com", "instagram.com"]):
                            results.append({
                                "title": title or query,
                                "url": href,
                                "source": "Web Search",
                                "year": "",
                                "poster": ""
                            })
    except Exception as e:
        logger.error(f"Internet search error: {e}")

    return results


async def resolve_real_url(url: str) -> str:
    """
    Yo'naltirish (redirect) va haqiqiy fayl havolasini topadi
    """
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.head(url, timeout=8, allow_redirects=True) as resp:
                return str(resp.url)
    except Exception:
        return url
