import random
from nonebot import on_message, get_plugin_config
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from nonebot.log import logger
from .config import Config

# 创建配置实例
config = get_plugin_config(Config)

# 禁言功能处理器
ban_matcher = on_message(priority=10, block=True)

@ban_matcher.handle()
async def handle_ban_commands(bot: Bot, event: GroupMessageEvent):
    """处理所有禁言相关命令"""
    # 检查是否是群消息
    if not isinstance(event, GroupMessageEvent):
        return
    
    # 检查功能是否开启
    if not config.enable_random_ban:
        return
    
    # 获取消息内容
    message_text = str(event.get_message()).strip()
    
    # 处理随机口球命令
    if message_text in ["随机口球", "我要口球"]:
        try:
            # 解析时间范围
            time_range = config.random_ban_time_range.split("-")
            min_time = int(time_range[0])
            max_time = int(time_range[1])
            
            # 生成随机禁言时间
            ban_time = random.randint(min_time, max_time)
            
            # 执行禁言
            await bot.set_group_ban(
                group_id=event.group_id,
                user_id=event.user_id,
                duration=ban_time
            )
            
            # 发送提示消息
            await ban_matcher.send(f"恭喜你获得了 {ban_time} 秒的口球时间！🤐")
            
        except Exception as e:
            logger.error(f"随机禁言功能执行失败: {e}")
            await ban_matcher.send("禁言失败，可能是权限不足或其他错误")
    
    # 处理禅定命令
    elif message_text in ["禅定", "精致睡眠"]:
        try:
            # 使用配置的长时间禁言时间
            ban_time = config.long_ban_time
            
            # 执行禁言
            await bot.set_group_ban(
                group_id=event.group_id,
                user_id=event.user_id,
                duration=ban_time
            )
            
            # 发送提示消息
            hours = ban_time // 3600
            await ban_matcher.send(f"开始进入 {hours} 小时的禅定状态，祝你睡个好觉！😴")
            
        except Exception as e:
            logger.error(f"禅定功能执行失败: {e}")
            await ban_matcher.send("禁言失败，可能是权限不足或其他错误")