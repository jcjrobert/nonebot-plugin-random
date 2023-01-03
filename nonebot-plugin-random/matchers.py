import random
import json
import shlex
import imghdr
import hashlib
from datetime import datetime
from pathlib import Path
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
from .download import *

data_path = Path() / "data" / "random"
COMMANDS = []

async def bot_send(
    path:Path, 
    type:str, 
    bot:Bot, 
    event:GroupMessageEvent,
    output_prefix:str,
    output_suffix:str,
    is_at_sender:bool,
):
    output_prefix = replace_message(output_prefix,path)
    output_suffix = replace_message(output_suffix,path)
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
    elif type == "video":
        await bot.send(
            event=event,
            message=MessageSegment.video(file=f"file:///{path.resolve()}")
        )

def get_files(
    dir_name: str,
    type: str,
):
    files = []
    dirs = [data_path.joinpath(dir_name)]
    while dirs:
        for i in dirs[0].iterdir():
            if is_file(type, i):
                files.append(i)
            elif i.is_dir():
                dirs.append(i)
        dirs.pop(0)
    return files

def create_matchers():
    def handler(
        dir_name: str, 
        config: RandomDetailConfig,
        is_specify: bool = False,
    ) -> T_Handler:
        async def handle(
            matcher: Matcher, 
            bot: Bot, 
            event: GroupMessageEvent,
            state: T_State,
        ):
            try:
                files = get_files(dir_name, config.draw_output)
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
                is_at_sender=config.is_at_sender,
            )

        return handle

    def insert_image_handler(
        dir_name: str,
        commands: List[str],
    ) -> T_Handler:
        async def handle(
            bot: Bot, 
            event: GroupMessageEvent,
        ):
            images: List[bytes] = []
            images_name: List[str] = []

            success: int = 0
            fail: int = 0

            if event.reply:
                for img in event.reply.message["image"]:
                    try:
                        _img = await download_url(str(img.data.get("url", "")))
                        success += 1
                        images.append(_img)
                    except:
                        fail += 1

            msg: Message = event.dict()["message"]
            for msg_seg in msg:
                if msg_seg.type == "image":
                    try:
                        _img = await download_url(str(msg_seg.data.get("url", "")))
                        success += 1
                        images.append(_img)
                    except:
                        fail += 1
                elif msg_seg.type == "text":
                    raw_text = str(msg_seg)
                    for command in commands:
                        raw_text = raw_text.replace(command, "")
                    try:
                        texts = shlex.split(raw_text)
                    except:
                        texts = raw_text.split()
                    images_name += texts
            
            base = 0
            while len(images_name) < len(images):
                images_name.append(str(int(datetime.now().timestamp())+base))
                base += 1
            images_name = images_name[:len(images)]
            images_name = [f"{img_name}.{imghdr.what(None, h=images[i])}" for i,img_name in enumerate(images_name)]

            path = data_path.joinpath(dir_name)
            for i,img in enumerate(images):
                img_path = path / images_name[i]
                with img_path.open("wb+") as f:
                    f.write(img)

            tosend = f"添加完成，成功{success}张，失败{fail}张，可以直接用于抽取"
            await bot.send(event=event,message=tosend,at_sender=True)

        return handle

    def delete_image_handler(
        dir_name: str
    ) -> T_Handler:
        async def handle(
            bot: Bot, 
            event: GroupMessageEvent,
        ):
            images: List[bytes] = []
            imgs_hash: List[str] = []

            """
            获取图片
            """
            if event.reply:
                for img in event.reply.message["image"]:
                    try:
                        _img = await download_url(str(img.data.get("url", "")))
                        images.append(_img)
                    except:
                        traceback.print_exc()
                        logger.error("删除图片读取失败")

            msg: Message = event.dict()["message"]
            for msg_seg in msg:
                if msg_seg.type == "image":
                    try:
                        _img = await download_url(str(msg_seg.data.get("url", "")))
                        images.append(_img)
                    except:
                        traceback.print_exc()
                        logger.error("删除图片读取失败")
            imgs_hash = [hashlib.md5(image).hexdigest() for image in images]

            files = get_files(dir_name, "image")  

            remove_file = 0
            for f in files:
                f_hash = hashlib.md5(f.read_bytes()).hexdigest()
                if f_hash in imgs_hash:
                    f.unlink()
                    remove_file += 1
            
            await bot.send(event=event,message=f"删除图片成功，一共删除了{remove_file}张图片",at_sender=True)

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
                    with config_path.open("r",encoding="UTF-8") as f:
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
                    rule=check_tome(config.is_tome),
                ).append_handler(
                    handler(
                        dir_name=dir_name,
                        config=config,
                        is_specify=True,
                    )
                )
                if config.draw_output == "image":
                    on_command(
                        config.insert_message[0],
                        aliases=set(config.insert_message[1:]),
                        block=True,
                        priority=12,
                        rule=check_tome(config.is_tome),
                        permission=check_modify(config.modify_admin_only),
                    ).append_handler(
                        insert_image_handler(
                            dir_name=dir_name,
                            commands=config.insert_message,
                        )
                    )
                    on_command(
                        config.delete_message[0],
                        aliases=set(config.delete_message[1:]),
                        block=True,
                        priority=12,
                        rule=check_tome(config.is_tome),
                        permission=check_modify(config.modify_admin_only),
                    ).append_handler(
                        delete_image_handler(
                            dir_name=dir_name,
                        )
                    )
            elif config.message_type == "keyword":
                COMMANDS.append(f"关键词含有{config.message[0]}{' 并@我' if config.is_tome else ''}")
                on_keyword(
                    config.message[0],
                    block=True,
                    priority=12,
                    rule=check_tome(config.is_tome),
                ).append_handler(
                    handler(
                        dir_name=dir_name,
                        config=config,
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
                    rule=check_tome(config.is_tome),
                ).append_handler(
                    handler(
                        dir_name=dir_name,
                        config=config,
                    )
                )

create_matchers()