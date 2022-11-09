from pathlib import Path
import random
import json
import traceback

from nonebot.matcher import Matcher
from nonebot.typing import T_Handler, T_State
from nonebot.params import _command_arg
from nonebot import logger
from nonebot import on_command, on_keyword, on_regex
from nonebot.adapters.onebot.v11 import (
    Bot,
    Message,
    MessageSegment,
    GroupMessageEvent
)

from .utils import *
from .depends import *
from .models import *

data_path = Path() / "data" / "random"
COMMANDS = []

async def bot_send(
    path:Path, 
    type:str, 
    bot:Bot, 
    event:GroupMessageEvent,
    output_prefix:str,
    output_suffix:str,
    is_at_sender:bool
):
    if type == "image":
        await bot.send(
            event=event,
            message=Message(output_prefix)+
                MessageSegment.image(file=f"file:///{path.resolve()}")+
                Message(output_suffix),
            at_sender=is_at_sender
        )
    elif type == "record":
        await bot.send(
            event=event,
            message=MessageSegment.record(file=f"file:///{path.resolve()}")
        )

def create_matchers():
    def handler(
        dir_name: str, 
        config: RandomDetailConfig,
        is_specify: bool = False
    ) -> T_Handler:
        async def handle(
            matcher: Matcher, 
            bot: Bot, 
            event: GroupMessageEvent,
            state: T_State,
        ):
            try:
                files = []
                dirs = [data_path.joinpath(dir_name)]
                while dirs:
                    for i in dirs[0].iterdir():
                        if is_file(config.draw_output, i):
                            files.append(i)
                        elif i.is_dir():
                            dirs.append(i)
                    dirs.pop(0)
                get_file = random.choice(files)
                if is_specify:
                    arg = str(_command_arg(state))
                    if arg:
                        for file in files:
                            if file.name.startswith(arg):
                                get_file = file
                                break
            except IndexError:
                traceback.print_exc()
                await matcher.finish(message=f"当前文件夹/{dir_name}下没有文件，请放置任意文件并配置好后再使用命令")
            except:
                traceback.print_exc()
                await matcher.finish(message="出现未知错误，请自行查看日志解决")
            await bot_send(
                path=get_file, 
                type=config.draw_output, 
                bot=bot, 
                event=event,
                output_prefix=config.output_prefix,
                output_suffix=config.output_suffix,
                is_at_sender=config.is_at_sender
            )

        return handle

    if not data_path.exists():
        data_path.mkdir(parents=True, exist_ok=True)
    for dir in data_path.iterdir():
        if dir.is_dir():
            dir_name = dir.name
            config_path = dir / "config.json"
            config_dict = {}
            if config_path.exists():
                try:
                    with config_path.open("r") as f:
                        config_dict = json.loads(f.read())
                except:
                    traceback.print_exc()
                    logger.error(f"/{dir_name}配置文件格式错误，请检查格式并进行重新配置")
            config = RandomDetailConfig(dir_name=dir_name,config_dict=config_dict)
            if config.message_type == "command":
                COMMANDS.append(("@我 + " if config.is_tome else "") + '/'.join(config.message))
                on_command(
                    config.message[0],
                    aliases=set(config.message[1:]),
                    block=True,
                    priority=12,
                    rule=check_tome(config.is_tome)
                ).append_handler(
                    handler(
                        dir_name=dir_name,
                        config=config,
                        is_specify=True
                    )
                )
            elif config.message_type == "keyword":
                COMMANDS.append(f"关键词含有{config.message[0]}{' 并@我' if config.is_tome else ''}")
                on_keyword(
                    config.message[0],
                    block=True,
                    priority=12,
                    rule=check_tome(config.is_tome)
                ).append_handler(
                    handler(
                        dir_name=dir_name,
                        config=config
                    )
                )
            elif config.message_type == "regex":
                if len(config.message) <= 1:
                    logger.error(f"/{dir_name}使用正则匹配时应保证message有两项，第一项是正则表达式，第二项是匹配表达式的命令（用于命令展示）")
                    continue
                COMMANDS.append(f"{'@我 + ' if config.is_tome else ''}{config.message[1]}")
                on_regex(
                    config.message[0],
                    block=True,
                    priority=12,
                    rule=check_tome(config.is_tome)
                ).append_handler(
                    handler(
                        dir_name=dir_name,
                        config=config
                    )
                )

create_matchers()