from __future__ import annotations

import asyncio
import shlex
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Type
from uuid import uuid4

from nonebot import on_command, on_keyword, on_regex
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_Handler
from nonebot_plugin_alconna import UniMessage

from .cooldown import group_cooldowns
from .data_source import (
    ARCHIVE_PATH,
    DATA_PATH,
    EmptyPoolError,
    RandomPoolError,
    ResourceNotFoundError,
    archive_pool,
    choose_pool_file_async,
    delete_images_by_content_async,
    get_pool_stats_async,
    load_all_pool_configs,
    read_resource,
    restore_pool,
    save_images_async,
    write_pool_config,
)
from .depends import check_modify, check_tome
from .download import DownloadError, download_url
from .models import RandomPoolConfig
from .switches import group_feature_switches
from .utils import replace_message


NAMESPACE = "random"
MANAGEMENT_COMMANDS = {
    "随机池列表",
    "开启随机池",
    "关闭随机池",
    "开启群随机池",
    "关闭群随机池",
    "全局启用随机池",
    "全局禁用随机池",
    "新增随机池",
    "编辑随机池",
    "删除随机池",
    "随机池归档列表",
    "恢复随机池",
}
MANAGEMENT_HELP_SECTIONS = (
    {
        "title": "查看资源池",
        "permission": "群成员",
        "commands": ("随机池列表",),
        "audience": "manager",
    },
    {
        "title": "群内开关",
        "permission": "群主、群管理员或超级管理员",
        "commands": (
            "开启随机池 <资源池ID...>",
            "关闭随机池 <资源池ID...>",
        ),
        "audience": "manager",
    },
    {
        "title": "跨群管理",
        "permission": "仅超级管理员",
        "commands": (
            "随机池列表 <群号>",
            "开启群随机池 <群号> <资源池ID...>",
            "关闭群随机池 <群号> <资源池ID...>",
        ),
        "audience": "superuser",
    },
    {
        "title": "全局默认",
        "permission": "仅超级管理员",
        "commands": (
            "全局禁用随机池 <资源池ID...>",
            "全局启用随机池 <资源池ID...>",
        ),
        "audience": "superuser",
    },
    {
        "title": "资源池管理",
        "permission": "仅超级管理员",
        "commands": (
            "新增随机池",
            "编辑随机池 <资源池ID>",
            "删除随机池 <资源池ID>",
            "随机池归档列表",
            "恢复随机池 <归档ID>",
        ),
        "audience": "superuser",
    },
)
MANAGEMENT_USAGE = [
    f"{section['title']}（{section['permission']}）："
    + "；".join(section["commands"])
    for section in MANAGEMENT_HELP_SECTIONS
]


class PoolRegistry:
    def __init__(self) -> None:
        self.configs: Dict[str, RandomPoolConfig] = {}
        self.matchers: Dict[str, List[Type[Matcher]]] = {}
        self._triggers: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._metadata: Optional[PluginMetadata] = None

    def bind_metadata(self, metadata: PluginMetadata) -> None:
        self._metadata = metadata
        self._refresh_metadata()

    def load_initial(self) -> None:
        for config in load_all_pool_configs():
            try:
                self.register(config)
            except Exception as error:
                logger.error(f"[random] 注册资源池 {config.pool_id} 失败：{error}")

    def register(self, config: RandomPoolConfig) -> None:
        if config.pool_id in self.configs or config.pool_id in self.matchers:
            raise RandomPoolError(f"资源池 {config.pool_id} 已注册")
        self._validate_conflicts(config, exclude_pool=config.pool_id)
        created: List[Type[Matcher]] = []
        try:
            created.extend(self._build_draw_matcher(config))
            if config.draw_output == "image":
                created.extend(self._build_image_management_matchers(config))
        except Exception:
            for matcher in created:
                matcher.destroy()
            raise
        self.configs[config.pool_id] = config
        self.matchers[config.pool_id] = created
        self._record_triggers(config)
        self._refresh_metadata()

    def unregister(self, pool_id: str) -> Optional[RandomPoolConfig]:
        config = self.configs.pop(pool_id, None)
        for matcher in self.matchers.pop(pool_id, []):
            matcher.destroy()
        self._drop_triggers(pool_id)
        self._refresh_metadata()
        return config

    async def create(self, config: RandomPoolConfig) -> None:
        async with self._lock:
            target = DATA_PATH / config.pool_id
            if target.exists() or config.pool_id in self.configs:
                raise RandomPoolError(f"资源池 {config.pool_id} 已存在")
            self._validate_conflicts(config)
            temporary = DATA_PATH / f".creating-{uuid4().hex}"
            await asyncio.to_thread(write_pool_config, temporary, config)
            await asyncio.to_thread(temporary.replace, target)
            try:
                self.register(config)
            except Exception:
                await asyncio.to_thread(shutil.rmtree, target, True)
                raise

    async def edit(self, pool_id: str, new_config: RandomPoolConfig) -> None:
        async with self._lock:
            old_config = self.configs.get(pool_id)
            if old_config is None:
                raise RandomPoolError(f"资源池 {pool_id} 不存在")
            if new_config.pool_id != pool_id:
                raise RandomPoolError("资源池 ID 不支持在线修改")
            self._validate_conflicts(new_config, exclude_pool=pool_id)
            pool_dir = DATA_PATH / pool_id
            await asyncio.to_thread(write_pool_config, pool_dir, new_config)
            self.unregister(pool_id)
            try:
                self.register(new_config)
            except Exception:
                await asyncio.to_thread(write_pool_config, pool_dir, old_config)
                self.register(old_config)
                raise

    async def archive(self, pool_id: str) -> str:
        async with self._lock:
            config = self.unregister(pool_id)
            if config is None:
                raise RandomPoolError(f"资源池 {pool_id} 不存在")
            try:
                archive_id = await asyncio.to_thread(archive_pool, pool_id)
            except Exception:
                self.register(config)
                raise
            await group_cooldowns.clear_pool(pool_id)
            try:
                await group_feature_switches.remove_feature(NAMESPACE, pool_id)
            except Exception as error:
                logger.warning(
                    f"[random] 资源池 {pool_id} 已归档，但清理群开关失败：{error}"
                )
            return archive_id

    async def restore(self, archive_id: str) -> RandomPoolConfig:
        async with self._lock:
            config = await asyncio.to_thread(restore_pool, archive_id)
            try:
                self.register(config)
            except Exception:
                target = DATA_PATH / config.pool_id
                ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
                await asyncio.to_thread(target.replace, ARCHIVE_PATH / archive_id)
                raise
            return config

    def metadata_usage(self) -> List[str]:
        return list(MANAGEMENT_USAGE)

    async def stats(self, pool_id: str) -> Tuple[int, int]:
        config = self.configs[pool_id]
        return await get_pool_stats_async(DATA_PATH / pool_id, config.draw_output)

    def _build_draw_matcher(self, config: RandomPoolConfig) -> List[Type[Matcher]]:
        rule = check_tome(config.is_tome)
        if config.message_type == "command":
            matcher = on_command(
                config.message[0],
                aliases=set(config.message[1:]),
                block=True,
                priority=12,
                rule=rule,
            )
            matcher.append_handler(self._draw_handler(config, accepts_argument=True))
        elif config.message_type == "keyword":
            matcher = on_keyword(
                set(config.message),
                block=True,
                priority=12,
                rule=rule,
            )
            matcher.append_handler(self._draw_handler(config, accepts_argument=False))
        else:
            matcher = on_regex(
                config.message[0],
                block=True,
                priority=12,
                rule=rule,
            )
            matcher.append_handler(self._draw_handler(config, accepts_argument=False))
        return [matcher]

    def _build_image_management_matchers(
        self,
        config: RandomPoolConfig,
    ) -> List[Type[Matcher]]:
        permission = check_modify(config.modify_admin_only)
        rule = check_tome(config.is_tome)
        created: List[Type[Matcher]] = []
        try:
            insert_matcher = on_command(
                config.insert_message[0],
                aliases=set(config.insert_message[1:]),
                block=True,
                priority=12,
                permission=permission,
                rule=rule,
            )
            insert_matcher.append_handler(self._insert_handler(config))
            created.append(insert_matcher)
            delete_matcher = on_command(
                config.delete_message[0],
                aliases=set(config.delete_message[1:]),
                block=True,
                priority=12,
                permission=permission,
                rule=rule,
            )
            delete_matcher.append_handler(self._delete_handler(config))
            created.append(delete_matcher)
            return created
        except Exception:
            for matcher in created:
                matcher.destroy()
            raise

    @staticmethod
    def _draw_handler(config: RandomPoolConfig, accepts_argument: bool) -> T_Handler:
        async def handle(
            bot: Bot,
            event: GroupMessageEvent,
            args: Message = CommandArg(),
        ) -> None:
            group_id = str(event.group_id)
            try:
                enabled = await group_feature_switches.is_enabled(
                    NAMESPACE,
                    group_id,
                    config.pool_id,
                )
            except Exception as error:
                logger.error(f"[random] 读取群开关失败：{error}")
                await bot.send(event, "随机池配置读取失败，请稍后再试")
                return
            if not enabled:
                return
            lease = await group_cooldowns.acquire(
                config.pool_id,
                group_id,
                config.cooldown_seconds,
            )
            if lease is None:
                return
            try:
                prefix = args.extract_plain_text().strip() if accepts_argument else ""
                path = await choose_pool_file_async(config, prefix)
                content = await read_resource(path, config.draw_output)
                output_prefix = replace_message(config.output_prefix, path)
                output_suffix = replace_message(config.output_suffix, path)
                if config.draw_output == "text":
                    await bot.send(
                        event,
                        output_prefix + content + output_suffix,
                        at_sender=config.is_at_sender,
                    )
                elif config.draw_output == "image":
                    await (
                        UniMessage.text(output_prefix)
                        + UniMessage.image(raw=content)
                        + UniMessage.text(output_suffix)
                    ).send(at_sender=config.is_at_sender)
                elif config.draw_output == "record":
                    await UniMessage.voice(raw=content).send()
                else:
                    await UniMessage.video(raw=content).send()
            except (EmptyPoolError, ResourceNotFoundError) as error:
                await group_cooldowns.release(lease)
                await bot.send(event, str(error))
            except Exception as error:
                await group_cooldowns.release(lease)
                logger.exception(f"[random] 资源池 {config.pool_id} 抽取失败：{error}")
                await bot.send(event, "随机素材发送失败，请稍后再试")

        return handle

    @staticmethod
    def _insert_handler(config: RandomPoolConfig) -> T_Handler:
        async def handle(
            bot: Bot,
            event: GroupMessageEvent,
            args: Message = CommandArg(),
        ) -> None:
            segments = []
            if event.reply:
                segments.extend(event.reply.message["image"])
            segments.extend(event.get_message()["image"])
            if not segments:
                await bot.send(event, "请附带图片或回复包含图片的消息", at_sender=True)
                return

            names_text = args.extract_plain_text().strip()
            try:
                names = shlex.split(names_text) if names_text else []
            except ValueError:
                names = names_text.split()
            contents: List[bytes] = []
            failed = 0
            for segment in segments:
                try:
                    contents.append(
                        await download_url(str(segment.data.get("url", "")))
                    )
                except DownloadError as error:
                    failed += 1
                    logger.warning(f"[random] 图片下载失败：{error}")
            if not contents:
                await bot.send(
                    event, f"没有可保存的图片，失败 {failed} 张", at_sender=True
                )
                return
            base = int(datetime.now().timestamp())
            while len(names) < len(contents):
                names.append(str(base + len(names)))
            try:
                saved = await save_images_async(
                    DATA_PATH / config.pool_id,
                    list(zip(contents, names[: len(contents)])),
                )
            except (ValueError, RandomPoolError) as error:
                await bot.send(event, f"添加失败：{error}", at_sender=True)
                return
            await bot.send(
                event,
                f"添加完成，成功 {len(saved)} 张，失败 {failed} 张",
                at_sender=True,
            )

        return handle

    @staticmethod
    def _delete_handler(config: RandomPoolConfig) -> T_Handler:
        async def handle(bot: Bot, event: GroupMessageEvent) -> None:
            segments = []
            if event.reply:
                segments.extend(event.reply.message["image"])
            segments.extend(event.get_message()["image"])
            if not segments:
                await bot.send(event, "请附带图片或回复包含图片的消息", at_sender=True)
                return
            contents: List[bytes] = []
            for segment in segments:
                try:
                    contents.append(
                        await download_url(str(segment.data.get("url", "")))
                    )
                except DownloadError as error:
                    logger.warning(f"[random] 删除比对图片下载失败：{error}")
            removed = await delete_images_by_content_async(
                DATA_PATH / config.pool_id,
                contents,
            )
            await bot.send(event, f"删除图片完成，共删除 {removed} 张", at_sender=True)

        return handle

    def _validate_conflicts(
        self,
        config: RandomPoolConfig,
        exclude_pool: Optional[str] = None,
    ) -> None:
        for trigger in self._config_triggers(config):
            owner = self._triggers.get(trigger)
            if owner and owner != exclude_pool:
                raise RandomPoolError(f"触发条件与资源池 {owner} 冲突：{trigger}")
            kind, value = trigger.split(":", 1)
            if kind == "command" and value in MANAGEMENT_COMMANDS:
                raise RandomPoolError(f"命令与管理指令冲突：{value}")

    def _record_triggers(self, config: RandomPoolConfig) -> None:
        self._drop_triggers(config.pool_id)
        for trigger in self._config_triggers(config):
            self._triggers[trigger] = config.pool_id

    def _drop_triggers(self, pool_id: str) -> None:
        for trigger in [
            key for key, owner in self._triggers.items() if owner == pool_id
        ]:
            self._triggers.pop(trigger, None)

    @staticmethod
    def _config_triggers(config: RandomPoolConfig) -> Set[str]:
        result: Set[str] = set()
        if config.message_type == "regex":
            result.add(f"regex:{config.message[0]}")
        else:
            result.update(f"{config.message_type}:{item}" for item in config.message)
        if config.draw_output == "image":
            result.update(f"command:{item}" for item in config.insert_message)
            result.update(f"command:{item}" for item in config.delete_message)
        return result

    def _refresh_metadata(self) -> None:
        if self._metadata is not None:
            self._metadata.usage = "\n".join(self.metadata_usage())


pool_registry = PoolRegistry()
