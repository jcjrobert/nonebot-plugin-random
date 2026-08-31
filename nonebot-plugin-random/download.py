from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import httpx
from nonebot.log import logger


MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024


class DownloadError(Exception):
    pass


async def download_url(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise DownloadError("仅支持 HTTP/HTTPS 图片地址")

    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        for attempt in range(1, 4):
            try:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
                        raise DownloadError("图片超过 20 MiB 限制")
                    chunks = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > MAX_DOWNLOAD_BYTES:
                            raise DownloadError("图片超过 20 MiB 限制")
                        chunks.append(chunk)
                    return b"".join(chunks)
            except DownloadError:
                raise
            except (httpx.HTTPError, ValueError) as error:
                logger.warning(f"[random] 下载 {url} 失败，尝试 {attempt}/3：{error}")
                if attempt < 3:
                    await asyncio.sleep(1)
    raise DownloadError(f"{url} 下载失败")
