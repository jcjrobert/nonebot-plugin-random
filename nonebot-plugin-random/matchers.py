from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Tuple

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot_plugin_waiter import waiter
from pydantic import ValidationError

from .data_source import RandomPoolError, list_archives
from .management import (
    build_pool_views,
    build_text_dashboard,
    get_group_name,
    parse_bool,
    parse_choice,
    parse_messages,
)
from .models import RandomPoolConfig
from .registry import MANAGEMENT_HELP_SECTIONS, NAMESPACE, pool_registry
from .render import render_pool_manager
from .switches import group_feature_switches


ADMIN_PERMISSION = SUPERUSER | GROUP_ADMIN | GROUP_OWNER


class ConversationCancelled(Exception):
    pass


def conversation(matcher: Matcher) -> Callable[[str], Any]:
    @waiter(waits=["message"], keep_session=True)
    async def receive(event: GroupMessageEvent) -> str:
        return event.get_plaintext().strip()

    async def ask(prompt: str) -> str:
        await matcher.send(prompt)
        response = await receive.wait(timeout=60)
        if response is None:
            raise ConversationCancelled("操作超时，已取消")
        if response.strip() == "取消":
            raise ConversationCancelled("操作已取消")
        return response.strip()

    return ask


def parse_pool_ids(raw: str) -> List[str]:
    pool_ids = list(dict.fromkeys(raw.split()))
    if not pool_ids:
        raise ValueError("请输入至少一个资源池 ID，多个 ID 使用空格分隔")
    missing = [pool_id for pool_id in pool_ids if pool_id not in pool_registry.configs]
    if missing:
        raise ValueError("资源池不存在：" + "、".join(missing))
    return pool_ids


def parse_target_group(raw: str) -> Tuple[str, List[str]]:
    parts = raw.split()
    if len(parts) < 2:
        raise ValueError("请输入群号和至少一个资源池 ID")
    group_id = parts[0]
    if not re.fullmatch(r"[1-9][0-9]*", group_id):
        raise ValueError("群号必须是正整数")
    return group_id, parse_pool_ids(" ".join(parts[1:]))


async def set_group_pools(
    bot: Bot,
    event: GroupMessageEvent,
    group_id: str,
    pool_ids: List[str],
    enabled: bool,
) -> None:
    action = "开启" if enabled else "关闭"
    try:
        await group_feature_switches.set_many_enabled(
            NAMESPACE,
            group_id,
            pool_ids,
            enabled,
        )
    except Exception as error:
        logger.error(f"[random] {action}群 {group_id} 随机池失败：{error}")
        await bot.send(event, "资源池开关保存失败，请查看日志")
        return
    group_name = await get_group_name(bot, group_id)
    await bot.send(
        event,
        f"已为 {group_name}（{group_id}）{action}随机池：{'、'.join(pool_ids)}",
    )


async def set_global_pools(
    bot: Bot,
    event: GroupMessageEvent,
    pool_ids: List[str],
    enabled: bool,
) -> None:
    try:
        await group_feature_switches.set_global_enabled(
            NAMESPACE,
            pool_ids,
            enabled,
        )
    except Exception as error:
        logger.error(f"[random] 更新全局默认随机池状态失败：{error}")
        await bot.send(event, "全局默认状态保存失败，请查看日志")
        return
    action = "移出" if enabled else "加入"
    await bot.send(
        event,
        f"已{action}全局默认禁用名单：{'、'.join(pool_ids)}",
    )


pool_dashboard = on_command(
    "随机池列表",
    priority=11,
    block=True,
)


@pool_dashboard.handle()
async def show_pool_dashboard(
    bot: Bot,
    event: GroupMessageEvent,
    args: Message = CommandArg(),
) -> None:
    is_superuser = await SUPERUSER(bot, event)
    is_manager = is_superuser or event.sender.role in {"admin", "owner"}
    target_group = args.extract_plain_text().strip()
    if target_group:
        if not is_superuser:
            await bot.send(event, "仅超级管理员可以按群号查看随机池")
            return
        if not re.fullmatch(r"[1-9][0-9]*", target_group):
            await bot.send(event, "群号必须是正整数")
            return
        group_id = target_group
        detailed = True
    else:
        group_id = str(event.group_id)
        detailed = is_manager

    try:
        group_name = await get_group_name(bot, group_id)
        title = f"{group_name}（{group_id}）随机池"
        pools = await build_pool_views(group_id, detailed=detailed)
        help_sections = []
        if detailed:
            help_sections = [
                section
                for section in MANAGEMENT_HELP_SECTIONS
                if section["audience"] == "manager" or is_superuser
            ]
        image = await render_pool_manager(
            title,
            pools,
            detailed=detailed,
            help_sections=help_sections,
        )
        await bot.send(event, MessageSegment.image(image))
    except Exception as error:
        logger.exception(f"[random] 随机池列表渲染失败：{error}")
        if "pools" in locals() and "title" in locals():
            await bot.send(
                event,
                build_text_dashboard(title, pools, detailed, help_sections),
            )
            return
        await bot.send(event, "随机池列表读取失败，请稍后再试")


enable_pool = on_command(
    "开启随机池",
    priority=11,
    block=True,
    permission=ADMIN_PERMISSION,
)


@enable_pool.handle()
async def enable_pool_handler(
    bot: Bot,
    event: GroupMessageEvent,
    args: Message = CommandArg(),
) -> None:
    try:
        pool_ids = parse_pool_ids(args.extract_plain_text())
    except ValueError as error:
        await bot.send(event, str(error))
        return
    await set_group_pools(bot, event, str(event.group_id), pool_ids, True)


disable_pool = on_command(
    "关闭随机池",
    priority=11,
    block=True,
    permission=ADMIN_PERMISSION,
)


@disable_pool.handle()
async def disable_pool_handler(
    bot: Bot,
    event: GroupMessageEvent,
    args: Message = CommandArg(),
) -> None:
    try:
        pool_ids = parse_pool_ids(args.extract_plain_text())
    except ValueError as error:
        await bot.send(event, str(error))
        return
    await set_group_pools(bot, event, str(event.group_id), pool_ids, False)


enable_group_pools = on_command(
    "开启群随机池",
    priority=11,
    block=True,
    permission=SUPERUSER,
)


@enable_group_pools.handle()
async def enable_group_pools_handler(
    bot: Bot,
    event: GroupMessageEvent,
    args: Message = CommandArg(),
) -> None:
    try:
        group_id, pool_ids = parse_target_group(args.extract_plain_text())
    except ValueError as error:
        await bot.send(event, str(error))
        return
    await set_group_pools(bot, event, group_id, pool_ids, True)


disable_group_pools = on_command(
    "关闭群随机池",
    priority=11,
    block=True,
    permission=SUPERUSER,
)


@disable_group_pools.handle()
async def disable_group_pools_handler(
    bot: Bot,
    event: GroupMessageEvent,
    args: Message = CommandArg(),
) -> None:
    try:
        group_id, pool_ids = parse_target_group(args.extract_plain_text())
    except ValueError as error:
        await bot.send(event, str(error))
        return
    await set_group_pools(bot, event, group_id, pool_ids, False)


globally_disable_pools = on_command(
    "全局禁用随机池",
    priority=11,
    block=True,
    permission=SUPERUSER,
)


@globally_disable_pools.handle()
async def globally_disable_pools_handler(
    bot: Bot,
    event: GroupMessageEvent,
    args: Message = CommandArg(),
) -> None:
    try:
        pool_ids = parse_pool_ids(args.extract_plain_text())
    except ValueError as error:
        await bot.send(event, str(error))
        return
    await set_global_pools(bot, event, pool_ids, False)


globally_enable_pools = on_command(
    "全局启用随机池",
    priority=11,
    block=True,
    permission=SUPERUSER,
)


@globally_enable_pools.handle()
async def globally_enable_pools_handler(
    bot: Bot,
    event: GroupMessageEvent,
    args: Message = CommandArg(),
) -> None:
    try:
        pool_ids = parse_pool_ids(args.extract_plain_text())
    except ValueError as error:
        await bot.send(event, str(error))
        return
    await set_global_pools(bot, event, pool_ids, True)


create_pool = on_command(
    "新增随机池",
    priority=11,
    block=True,
    permission=SUPERUSER,
)


@create_pool.handle()
async def create_pool_handler(
    bot: Bot, event: GroupMessageEvent, matcher: Matcher
) -> None:
    ask = conversation(matcher)
    try:
        pool_id = await ask("请输入资源池 ID（小写字母、数字、_、-，或发送“取消”）：")
        display_name = await ask("请输入展示名称：")
        draw_output = parse_choice(
            "output",
            await ask("请输入输出类型：文本 / 图片 / 语音 / 视频"),
        )
        message_type = parse_choice(
            "message_type",
            await ask("请输入匹配类型：命令 / 关键词 / 正则"),
        )
        trigger_tip = (
            "请输入“正则表达式|展示文本”："
            if message_type == "regex"
            else "请输入触发条件，多个别名使用 | 分隔："
        )
        messages = parse_messages(
            await ask(trigger_tip),
            regex=message_type == "regex",
        )
        draw_mode = parse_choice(
            "mode",
            await ask("请输入抽取模式：直接 / 分层"),
        )
        cooldown_text = await ask("请输入群级 CD 秒数（非负整数，默认建议 10）：")
        cooldown_seconds = int(cooldown_text)
        config = RandomPoolConfig(
            pool_id=pool_id,
            display_name=display_name,
            draw_output=draw_output,
            message_type=message_type,
            message=messages,
            draw_mode=draw_mode,
            cooldown_seconds=cooldown_seconds,
        )
        summary = json.dumps(config.to_config_dict(), ensure_ascii=False, indent=2)
        if await ask(f"请确认配置：\n{summary}\n输入“确认创建”继续：") != "确认创建":
            raise ConversationCancelled("未确认创建，操作已取消")
        await pool_registry.create(config)
        await bot.send(event, f"资源池 {pool_id} 创建成功，matcher 已即时生效")
    except ConversationCancelled as error:
        await bot.send(event, str(error))
    except (ValueError, ValidationError, RandomPoolError) as error:
        await bot.send(event, f"创建失败：{error}")
    except Exception as error:
        logger.exception(f"[random] 动态创建资源池失败：{error}")
        await bot.send(event, "创建失败，请查看日志")


EDIT_FIELDS: Dict[str, str] = {
    "名称": "display_name",
    "输出类型": "draw_output",
    "抽取模式": "draw_mode",
    "匹配类型": "message_type",
    "触发": "message",
    "冷却": "cooldown_seconds",
    "要求AT": "is_tome",
    "前缀": "output_prefix",
    "后缀": "output_suffix",
    "回复AT": "is_at_sender",
    "添加命令": "insert_message",
    "删除命令": "delete_message",
    "修改仅管理": "modify_admin_only",
}


def apply_edit(raw: Dict[str, Any], field: str, value: str) -> None:
    key = EDIT_FIELDS.get(field)
    if key is None:
        raise ValueError("未知字段")
    if key == "draw_output":
        raw[key] = parse_choice("output", value)
    elif key == "draw_mode":
        raw[key] = parse_choice("mode", value)
    elif key == "message_type":
        raw[key] = parse_choice("message_type", value)
    elif key in {"message", "insert_message", "delete_message"}:
        raw[key] = parse_messages(
            value, regex=key == "message" and raw.get("message_type") == "regex"
        )
    elif key == "cooldown_seconds":
        raw[key] = int(value)
    elif key in {"is_tome", "is_at_sender", "modify_admin_only"}:
        raw[key] = parse_bool(value)
    else:
        raw[key] = value


edit_pool = on_command(
    "编辑随机池",
    priority=11,
    block=True,
    permission=SUPERUSER,
)


@edit_pool.handle()
async def edit_pool_handler(
    bot: Bot,
    event: GroupMessageEvent,
    matcher: Matcher,
    args: Message = CommandArg(),
) -> None:
    pool_id = args.extract_plain_text().strip()
    current = pool_registry.configs.get(pool_id)
    if current is None:
        await bot.send(event, "资源池不存在")
        return
    ask = conversation(matcher)
    raw = current.to_config_dict()
    fields = " / ".join(EDIT_FIELDS)
    try:
        while True:
            field = await ask(
                f"当前配置：\n{json.dumps(raw, ensure_ascii=False, indent=2)}\n"
                f"输入要修改的字段（{fields}），或输入“完成”："
            )
            if field == "完成":
                break
            value = await ask(f"请输入“{field}”的新值：")
            apply_edit(raw, field, value)
        config = RandomPoolConfig.from_dict(pool_id, raw)
        if await ask("输入“确认保存”应用配置并重建 matcher：") != "确认保存":
            raise ConversationCancelled("未确认保存，操作已取消")
        await pool_registry.edit(pool_id, config)
        await bot.send(event, f"资源池 {pool_id} 已更新，matcher 已重建")
    except ConversationCancelled as error:
        await bot.send(event, str(error))
    except (ValueError, ValidationError, RandomPoolError) as error:
        await bot.send(event, f"编辑失败：{error}")
    except Exception as error:
        logger.exception(f"[random] 编辑资源池失败：{error}")
        await bot.send(event, "编辑失败，请查看日志")


delete_pool = on_command(
    "删除随机池",
    priority=11,
    block=True,
    permission=SUPERUSER,
)


@delete_pool.handle()
async def delete_pool_handler(
    bot: Bot,
    event: GroupMessageEvent,
    matcher: Matcher,
    args: Message = CommandArg(),
) -> None:
    pool_id = args.extract_plain_text().strip()
    config = pool_registry.configs.get(pool_id)
    if config is None:
        await bot.send(event, "资源池不存在")
        return
    count, size = await pool_registry.stats(pool_id)
    ask = conversation(matcher)
    try:
        confirmation = await ask(
            f"将归档 {config.display_name} ({pool_id})，有效素材 {count} 个，"
            f"约 {size / 1024 / 1024:.2f} MiB。请输入完整 ID 确认："
        )
        if confirmation != pool_id:
            raise ConversationCancelled("确认 ID 不一致，操作已取消")
        archive_id = await pool_registry.archive(pool_id)
        await bot.send(event, f"资源池已归档：{archive_id}")
    except ConversationCancelled as error:
        await bot.send(event, str(error))
    except Exception as error:
        logger.exception(f"[random] 归档资源池失败：{error}")
        await bot.send(event, f"归档失败：{error}")


archive_list = on_command(
    "随机池归档列表",
    priority=11,
    block=True,
    permission=SUPERUSER,
)


@archive_list.handle()
async def archive_list_handler(bot: Bot, event: GroupMessageEvent) -> None:
    archives = list_archives()
    if not archives:
        await bot.send(event, "暂无随机池归档")
        return
    await bot.send(event, "随机池归档：\n" + "\n".join(path.name for path in archives))


restore_pool_matcher = on_command(
    "恢复随机池",
    priority=11,
    block=True,
    permission=SUPERUSER,
)


@restore_pool_matcher.handle()
async def restore_pool_handler(
    bot: Bot,
    event: GroupMessageEvent,
    args: Message = CommandArg(),
) -> None:
    archive_id = args.extract_plain_text().strip()
    if not archive_id:
        await bot.send(event, "请输入归档 ID，可通过“随机池归档列表”查询")
        return
    try:
        config = await pool_registry.restore(archive_id)
        await bot.send(event, f"资源池 {config.pool_id} 已恢复并即时生效")
    except Exception as error:
        logger.exception(f"[random] 恢复资源池失败：{error}")
        await bot.send(event, f"恢复失败：{error}")
