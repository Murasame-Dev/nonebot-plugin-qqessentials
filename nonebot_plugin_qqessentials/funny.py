import random
from nonebot import on_keyword, get_plugin_config
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message
from nonebot.log import logger
from .config import Config

# 创建配置实例
config = get_plugin_config(Config)

# 1.随机禁言命令匹配器 L16
random_ban_matcher = on_keyword({"随机口球", "我要口球"}, priority=10, block=True)
# 2.禅定命令匹配器 L50
meditation_matcher = on_keyword({"禅定", "精致睡眠"}, priority=10, block=True)

# 1
@random_ban_matcher.handle()
async def handle_random_ban(bot: Bot, event: GroupMessageEvent):
    """处理随机禁言命令"""
    # 检查是否是群消息
    if not isinstance(event, GroupMessageEvent):
        return
    
    # 检查功能是否开启
    if not config.enable_random_ban:
        return
    
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
        
        # 记录日志
        logger.info(f"随机禁言执行成功，用户：{event.user_id}，时长：{ban_time}秒")
        
    except Exception as e:
        logger.error(f"随机禁言功能执行失败: {e}")

# 2
@meditation_matcher.handle()
async def handle_meditation(bot: Bot, event: GroupMessageEvent):
    """处理禅定命令"""
    # 检查是否是群消息
    if not isinstance(event, GroupMessageEvent):
        return
    
    # 检查功能是否开启
    if not config.enable_random_ban:
        return
    
    try:
        # 使用配置的长时间禁言时间
        ban_time = config.long_ban_time
        
        # 执行禁言
        await bot.set_group_ban(
            group_id=event.group_id,
            user_id=event.user_id,
            duration=ban_time
        )
        
        # 记录日志
        hours = ban_time // 3600
        logger.info(f"禅定执行成功，用户：{event.user_id}，时长：{hours}小时")
        
    except Exception as e:
        logger.error(f"禅定功能执行失败: {e}")