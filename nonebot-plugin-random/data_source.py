from __future__ import annotations

import asyncio
import hashlib
import io
import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from nonebot.log import logger
from PIL import Image

from .models import RandomPoolConfig
from .utils import is_file, validate_file_stem


DATA_PATH = Path("data") / "random"
ARCHIVE_PATH = Path("data") / "random_archive"

IMAGE_FORMAT_EXTENSIONS = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "GIF": ".gif",
    "WEBP": ".webp",
}


class RandomPoolError(Exception):
    pass


class PoolNotFoundError(RandomPoolError):
    pass


class EmptyPoolError(RandomPoolError):
    pass


class ResourceNotFoundError(RandomPoolError):
    pass


class InvalidImageError(RandomPoolError):
    pass


def load_pool_config(pool_dir: Path) -> RandomPoolConfig:
    config_path = pool_dir / "config.json"
    raw = {}
    if config_path.exists():
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("config.json 必须是 JSON 对象")
    return RandomPoolConfig.from_dict(pool_dir.name, raw)


def load_all_pool_configs(data_path: Path = DATA_PATH) -> List[RandomPoolConfig]:
    data_path.mkdir(parents=True, exist_ok=True)
    configs: List[RandomPoolConfig] = []
    for pool_dir in sorted(data_path.iterdir(), key=lambda item: item.name):
        if not pool_dir.is_dir() or pool_dir.name.startswith((".", "_")):
            continue
        try:
            configs.append(load_pool_config(pool_dir))
        except Exception as error:
            logger.error(f"[random] 资源池 {pool_dir.name} 配置无效，已跳过：{error}")
    return configs


def write_pool_config(pool_dir: Path, config: RandomPoolConfig) -> None:
    pool_dir.mkdir(parents=True, exist_ok=True)
    config_path = pool_dir / "config.json"
    temporary = config_path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(config.to_config_dict(), ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    temporary.replace(config_path)


def list_pool_files(pool_dir: Path, output_type: str) -> List[Path]:
    if not pool_dir.is_dir():
        raise PoolNotFoundError(f"资源池 {pool_dir.name} 不存在")
    return [path for path in pool_dir.rglob("*") if is_file(output_type, path)]


def choose_pool_file(
    config: RandomPoolConfig,
    prefix: str = "",
    data_path: Path = DATA_PATH,
    randomizer: random.Random = random,
) -> Path:
    pool_dir = data_path / config.pool_id
    if config.draw_mode == "direct":
        candidates = list_pool_files(pool_dir, config.draw_output)
    else:
        groups: List[List[Path]] = []
        for child in sorted(pool_dir.iterdir(), key=lambda item: item.name):
            if not child.is_dir():
                continue
            child_candidates = list_pool_files(child, config.draw_output)
            if child_candidates:
                groups.append(child_candidates)
        candidates = randomizer.choice(groups) if groups else []

    if not candidates:
        raise EmptyPoolError(f"资源池 {config.display_name} 暂无可用素材")
    if prefix:
        matched = [path for path in candidates if path.name.startswith(prefix)]
        if not matched:
            raise ResourceNotFoundError(f"未找到以 {prefix} 开头的素材")
        candidates = matched
    return randomizer.choice(candidates)


async def choose_pool_file_async(
    config: RandomPoolConfig,
    prefix: str = "",
    data_path: Path = DATA_PATH,
) -> Path:
    return await asyncio.to_thread(choose_pool_file, config, prefix, data_path)


async def read_resource(path: Path, output_type: str):
    if output_type == "text":
        return await asyncio.to_thread(path.read_text, encoding="utf-8")
    return await asyncio.to_thread(path.read_bytes)


def detect_image_extension(content: bytes) -> str:
    try:
        with Image.open(io.BytesIO(content)) as image:
            image_format = image.format
            image.verify()
    except Exception as error:
        raise InvalidImageError("文件不是有效图片") from error
    extension = IMAGE_FORMAT_EXTENSIONS.get(str(image_format).upper())
    if not extension:
        raise InvalidImageError("仅支持 PNG、JPEG、GIF、WebP 图片")
    return extension


def _unique_path(pool_dir: Path, stem: str, extension: str) -> Path:
    candidate = pool_dir / f"{stem}{extension}"
    index = 2
    while candidate.exists():
        candidate = pool_dir / f"{stem}_{index}{extension}"
        index += 1
    return candidate


def save_images(pool_dir: Path, images: Sequence[Tuple[bytes, str]]) -> List[Path]:
    pool_dir.mkdir(parents=True, exist_ok=True)
    validated: List[Tuple[bytes, str, str]] = []
    for content, raw_name in images:
        stem = validate_file_stem(raw_name)
        extension = detect_image_extension(content)
        validated.append((content, stem, extension))

    saved: List[Path] = []
    for content, stem, extension in validated:
        target = _unique_path(pool_dir, stem, extension)
        target.write_bytes(content)
        saved.append(target)
    return saved


async def save_images_async(
    pool_dir: Path,
    images: Sequence[Tuple[bytes, str]],
) -> List[Path]:
    return await asyncio.to_thread(save_images, pool_dir, images)


def delete_images_by_content(pool_dir: Path, images: Iterable[bytes]) -> int:
    hashes = {hashlib.md5(content).digest() for content in images}
    if not hashes:
        return 0
    removed = 0
    for path in list_pool_files(pool_dir, "image"):
        try:
            if hashlib.md5(path.read_bytes()).digest() in hashes:
                path.unlink()
                removed += 1
        except OSError as error:
            logger.warning(f"[random] 删除素材 {path} 失败：{error}")
    return removed


async def delete_images_by_content_async(
    pool_dir: Path, images: Iterable[bytes]
) -> int:
    return await asyncio.to_thread(delete_images_by_content, pool_dir, list(images))


def get_pool_stats(pool_dir: Path, output_type: str) -> Tuple[int, int]:
    files = list_pool_files(pool_dir, output_type)
    return len(files), sum(path.stat().st_size for path in files)


async def get_pool_stats_async(pool_dir: Path, output_type: str) -> Tuple[int, int]:
    return await asyncio.to_thread(get_pool_stats, pool_dir, output_type)


def archive_pool(pool_id: str) -> str:
    source = DATA_PATH / pool_id
    if not source.is_dir():
        raise PoolNotFoundError(f"资源池 {pool_id} 不存在")
    ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    archive_id = f"{timestamp}--{pool_id}"
    source.replace(ARCHIVE_PATH / archive_id)
    return archive_id


def list_archives() -> List[Path]:
    if not ARCHIVE_PATH.exists():
        return []
    return sorted(
        (path for path in ARCHIVE_PATH.iterdir() if path.is_dir()),
        key=lambda item: item.name,
        reverse=True,
    )


def restore_pool(archive_id: str) -> RandomPoolConfig:
    if not re.fullmatch(r"\d{20}--[a-z0-9][a-z0-9_-]{0,31}", archive_id):
        raise PoolNotFoundError("归档 ID 格式无效")
    source = ARCHIVE_PATH / archive_id
    if not source.is_dir():
        raise PoolNotFoundError(f"归档 {archive_id} 不存在")
    pool_id = archive_id.split("--", 1)[1]
    target = DATA_PATH / pool_id
    if target.exists():
        raise RandomPoolError(f"资源池 {pool_id} 已存在")
    config_path = source / "config.json"
    raw = (
        json.loads(config_path.read_text(encoding="utf-8"))
        if config_path.exists()
        else {}
    )
    config = RandomPoolConfig.from_dict(pool_id, raw)
    source.replace(target)
    return config
