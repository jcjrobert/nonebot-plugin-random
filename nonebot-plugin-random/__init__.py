from nonebot import require
from nonebot.plugin import PluginMetadata


require("nonebot_plugin_alconna")
require("nonebot_plugin_waiter")

from .registry import pool_registry  # noqa: E402


pool_registry.load_initial()
COMMANDS = pool_registry.metadata_usage()

__version__ = "0.1.0"
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

pool_registry.bind_metadata(__plugin_meta__)

from . import matchers as _matchers  # noqa: E402,F401
