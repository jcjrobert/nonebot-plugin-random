from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Sequence

from nonebot.adapters.onebot.v11 import Bot
from nonebot.log import logger

from .data_source import DATA_PATH, get_pool_stats_async
from .models import PoolView, RandomPoolConfig
from .registry import NAMESPACE, pool_registry
from .switches import group_feature_switches


CHOICES: Dict[str, Dict[str, str]] = {
    "output": {
        "文本": "text",
        "图片": "image",
        "语音": "record",
        "视频": "video",
        "text": "text",
        "image": "image",
        "record": "record",
        "video": "video",
    },
    "message_type": {
        "命令": "command",
        "关键词": "keyword",
        "正则": "regex",
        "command": "command",
        "keyword": "keyword",
        "regex": "regex",
    },
    "mode": {
        "直接": "direct",
        "分层": "indirect",
        "direct": "direct",
        "indirect": "indirect",
    },
}


def parse_choice(group: str, value: str) -> str:
    result = CHOICES[group].get(value.strip().casefold())
    if result is None:
        result = CHOICES[group].get(value.strip())
    if result is None:
        raise ValueError("选项无效")
    return result


def parse_bool(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"是", "开", "开启", "true", "1", "yes"}:
        return True
    if normalized in {"否", "关", "关闭", "false", "0", "no"}:
        return False
    raise ValueError("请输入 是/否")


def parse_messages(value: str, regex: bool = False) -> List[str]:
    items = [item.strip() for item in value.split("|") if item.strip()]
    if not items:
        raise ValueError("至少需要一个触发条件")
    if regex and len(items) < 2:
        raise ValueError("正则触发请使用“表达式|展示文本”格式")
    return items


async def get_group_name(bot: Bot, group_id: str) -> str:
    try:
        group_info = await bot.get_group_info(group_id=int(group_id))
        group_name = str(group_info.get("group_name", "")).strip()
        if group_name:
            return group_name
    except Exception as error:
        logger.warning(f"[random] 获取群 {group_id} 名称失败：{error}")
    return "未知群聊"


async def build_pool_views(group_id: str, detailed: bool) -> List[PoolView]:
    configs = [pool_registry.configs[key] for key in sorted(pool_registry.configs)]
    states = await group_feature_switches.get_states(
        NAMESPACE,
        group_id,
        (config.pool_id for config in configs),
    )

    async def build(config: RandomPoolConfig) -> PoolView:
        state = states[config.pool_id]
        stats = await get_pool_stats_async(
            DATA_PATH / config.pool_id,
            config.draw_output,
        )
        return PoolView(
            pool_id=config.pool_id,
            display_name=config.display_name,
            draw_output=config.draw_output,
            draw_mode=config.draw_mode,
            cooldown_seconds=config.cooldown_seconds,
            command=config.help_text,
            file_count=stats[0],
            enabled=state.enabled,
            switch_source=state.source,
            global_disabled=state.global_disabled,
        )

    if detailed:
        return await asyncio.gather(*(build(config) for config in configs))

    return [
        PoolView(
            pool_id=config.pool_id,
            display_name=config.display_name,
            draw_output=config.draw_output,
            draw_mode=config.draw_mode,
            cooldown_seconds=config.cooldown_seconds,
            command=config.help_text,
            enabled=states[config.pool_id].enabled,
            switch_source=states[config.pool_id].source,
            global_disabled=states[config.pool_id].global_disabled,
        )
        for config in configs
        if states[config.pool_id].enabled
    ]


def build_text_dashboard(
    title: str,
    pools: List[PoolView],
    detailed: bool,
    help_sections: Sequence[Dict[str, Any]],
) -> str:
    lines = [title]
    if not pools:
        lines.append("暂无随机池" if detailed else "当前群暂无已启用的随机功能")
    for pool in pools:
        if detailed:
            lines.append(
                f"[{pool.status_text}] {pool.display_name} ({pool.pool_id}) | "
                f"{pool.output_text}/{pool.mode_text} | {pool.file_count} 个 | "
                f"CD {pool.cooldown_seconds}s | {pool.command}"
            )
        else:
            lines.append(
                f"{pool.display_name} | {pool.output_text} | {pool.command}"
            )
    if help_sections:
        lines.append("\n相关指令：")
        for section in help_sections:
            lines.append(f"{section['title']}（{section['permission']}）")
            lines.extend(f"- {command}" for command in section["commands"])
    return "\n".join(lines)
