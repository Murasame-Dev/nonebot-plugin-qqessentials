from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from . import __main__ as __main__
from . import friend as friend
from . import group as group


from .config import Config

__version__ = "0.1.2"
__plugin_meta__ = PluginMetadata(
    name="QQEssentials",
    description="一个能够满足你很多需求的基础插件！",
    usage="目前支持:点赞，撤回，设精，禁言，发送消息等更多操作，后续会持续更新！",
    type="application",
    homepage="https://github.com/Murasame-Dev/nonebot-plugin-qqessentials",
    supported_adapters= {"~onebot.v11"},
    config=Config,
)

config = get_plugin_config(Config)
