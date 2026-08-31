from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Optional, Set


FILE_EXTENSIONS: Dict[str, Set[str]] = {
    "text": {".txt"},
    "image": {".gif", ".png", ".jpg", ".jpeg", ".webp"},
    "record": {".mp3", ".wav", ".ogg", ".flac"},
    "video": {".mp4", ".avi", ".flv", ".wmv", ".mov", ".mpg", ".mpeg"},
}

WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def get_file_type(path: Path) -> Optional[str]:
    suffix = path.suffix.casefold()
    for file_type, extensions in FILE_EXTENSIONS.items():
        if suffix in extensions:
            return file_type
    return None


def is_file(file_type: str, path: Path) -> bool:
    return path.is_file() and get_file_type(path) == file_type


def replace_message(message: str, path: Path) -> str:
    return message.replace("{filename}", path.name).replace("{filestem}", path.stem)


def validate_file_stem(raw_name: str) -> str:
    name = raw_name.strip()
    if not name:
        raise ValueError("文件名不能为空")
    if len(name) > 100:
        raise ValueError("文件名不能超过 100 个字符")
    if any(character in name for character in ("/", "\\")):
        raise ValueError("文件名不能包含路径分隔符")
    if os.path.isabs(name) or name in {".", ".."}:
        raise ValueError("文件名不能是绝对路径或相对路径")
    if any(ord(character) < 32 for character in name):
        raise ValueError("文件名不能包含控制字符")

    stem = Path(name).stem.strip().rstrip(". ")
    if not stem or stem.startswith("."):
        raise ValueError("文件名格式无效")
    if stem.upper() in WINDOWS_RESERVED_NAMES:
        raise ValueError("文件名是 Windows 保留名称")
    if re.search(r'[<>:"|?*]', stem):
        raise ValueError("文件名包含 Windows 不允许的字符")
    return stem
