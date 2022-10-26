from pathlib import Path
import random
import json
import traceback

from nonebot.matcher import Matcher
from nonebot.typing import T_Handler
from nonebot import logger
from nonebot import on_command, on_keyword
from nonebot.adapters.onebot.v11 import (
    Bot,
    Message,
    MessageSegment,
    GroupMessageEvent
)

from .utils import *
from .depends import *

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
        dir_name:str, 
        draw_output:str, 
        draw_mode:str,
        output_prefix:str,
        output_suffix:str,
        is_at_sender:bool
    ) -> T_Handler:
        async def handle(
            matcher: Matcher, 
            bot: Bot, 
            event: GroupMessageEvent
        ):
            try:
                if draw_mode == "direct":
                    get_file = random.choice([i for i in data_path.joinpath(dir_name).iterdir() if is_file(draw_output, i)])
                else:
                    file_type = random.choice([i for i in data_path.joinpath(dir_name).iterdir() if i.is_dir()])
                    get_file = random.choice([i for i in file_type.iterdir() if is_file(draw_output, i)])
            except IndexError:
                traceback.print_exc()
                await matcher.finish(message=f"当前文件夹/{dir_name}下没有文件，请放置任意文件并配置好后再使用命令")
            except:
                traceback.print_exc()
                await matcher.finish(message="出现未知错误，请自行查看日志解决")
            await bot_send(
                path=get_file, 
                type=draw_output, 
                bot=bot, 
                event=event,
                output_prefix=output_prefix,
                output_suffix=output_suffix,
                is_at_sender=is_at_sender
            )

        return handle

    if not data_path.exists():
        data_path.mkdir(parents=True, exist_ok=True)
    for dir in data_path.iterdir():
        if dir.is_dir():
            dir_name = dir.name
            draw_output = "image"
            draw_mode = "direct"
            message_type = "command"
            message = [f"随机{dir_name}"]
            is_tome = False
            output_prefix = ""
            output_suffix = ""
            is_at_sender = False
            config_path = dir / "config.json"
            if config_path.exists():
                try:
                    with config_path.open("r") as f:
                        config = json.loads(f.read())
                        if "draw_output" in config and config["draw_output"] in ["text","image","record"]:
                            draw_output = config["draw_output"]
                        if "draw_mode" in config and config["draw_mode"] in ["direct","indirect"]:
                            draw_mode = config["draw_mode"]
                        if "message_type" in config and config["message_type"] in ["command","keyword","regex"]:
                            message_type = config["message_type"]
                        if "message" in config and config["message"]:
                            message = config["message"]
                        if "is_tome" in config and isinstance(config["is_tome"], bool):
                            is_tome = config["is_tome"]
                        if "output_prefix" in config and config["output_prefix"]:
                            output_prefix = config["output_prefix"]
                        if "output_suffix" in config and config["output_suffix"]:
                            output_suffix = config["output_suffix"]
                        if "is_at_sender" in config and isinstance(config["is_at_sender"], bool):
                            is_at_sender = config["is_at_sender"]
                except:
                    traceback.print_exc()
                    logger.error(f"/{dir_name}配置文件有误，请重新配置")
            if message_type == "command":
                COMMANDS.append(("@我 + " if is_tome else "") + '/'.join(message))
                on_command(
                    message[0],
                    aliases=set(message[1:]),
                    block=True,
                    priority=12,
                    rule=check_tome(is_tome)
                ).append_handler(
                    handler(
                        dir_name=dir_name,
                        draw_output=draw_output,
                        draw_mode=draw_mode,
                        output_prefix=output_prefix,
                        output_suffix=output_suffix,
                        is_at_sender=is_at_sender
                    )
                )
            elif message_type == "keyword":
                COMMANDS.append(f"关键词含有{message[0]}{' 并@我' if is_tome else ''}")
                on_keyword(
                    message[0],
                    block=True,
                    priority=12,
                    rule=check_tome(is_tome)
                ).append_handler(
                    handler(
                        dir_name=dir_name,
                        draw_output=draw_output,
                        draw_mode=draw_mode,
                        output_prefix=output_prefix,
                        output_suffix=output_suffix,
                        is_at_sender=is_at_sender
                    )
                )

create_matchers()