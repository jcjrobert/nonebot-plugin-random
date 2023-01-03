from .matchers import *
from nonebot.plugin import PluginMetadata

__version__ = "0.0.9"
__plugin_meta__ = PluginMetadata(
    name="随机抽图/语音",
    description="Nonebot2 通用抽图/语音插件",
    usage="\n".join(COMMANDS),
    extra={
        "version": __version__,
        "license": "MIT",
        "author": "jcjrobert <jcjrobbie@gmail.com>",
    },
)