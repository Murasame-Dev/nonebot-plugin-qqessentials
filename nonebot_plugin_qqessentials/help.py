from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.permission import SUPERUSER

# 添加帮助命令
help_command = on_command("QQEss帮助", aliases={"qqess帮助"}, priority=10, permission=SUPERUSER)
help_msg_command = on_command("消息发送帮助", priority=10, permission=SUPERUSER)
help_group_command = on_command("群组管理帮助", priority=10, permission=SUPERUSER)
help_status_command = on_command("状态帮助", priority=10, permission=SUPERUSER)

@help_command.handle()
async def handle_help(bot: Bot, event: MessageEvent):
    """显示帮助信息主页"""
    help_text = """🤖 QQ机器人功能列表
━━━━━━━━━━━━━━━━
📋 基础功能：
  └ /机器人信息 - 查看机器人基本信息

✏️ 个人设置：
  ├ /修改个性签名 内容 - 修改个性签名
  ├ /修改头像 - 修改QQ头像
  └ /状态设置 [参数] - 设置在线状态

🗑️ 消息管理：
  └ /撤回 或 /撤 - 引用消息回复撤回（同时撤回被引用消息和指令消息）

🎯 互动功能：
  ├ 戳我 - 戳自己（无需指令头）
  ├ 戳 - 戳自己（无需指令头）
  ├ 戳 QQ号 - 戳指定QQ号（无需指令头）
  ├ 戳@某人 - 戳@的用户（无需指令头）
  └ 赞我 - 点赞功能（无需指令头，需要是好友）

💬 消息发送：[展开请用: /消息发送帮助]
🏷️ 群组管理：[展开请用: /群组管理帮助]
🔧 状态设置：[展开请用: /状态帮助]
━━━━━━━━━━━━━━━━
⚠️ 注意：管理功能大部分仅限超级用户使用
Ciallo～(∠・ω< )⌒★"""
    
    await help_command.send(help_text)

@help_msg_command.handle()
async def handle_help_msg(bot: Bot, event: MessageEvent):
    """显示消息发送功能帮助"""
    help_text = """💬 消息发送功能详细说明
━━━━━━━━━━━━━━━━
📤 发送功能：
  ├ /发送私聊消息 QQ号 内容 - 发送私聊消息
  ├ /发送群消息 群号 内容 - 发送群消息
  └ /删除好友 QQ号 - 删除指定QQ好友（需配置启用）

💡 使用说明：
  • 发送消息功能仅SUPERUSER可用
  • 删除好友功能默认关闭，需配置启用
  • 支持发送文本消息到指定私聊或群聊
━━━━━━━━━━━━━━━━
👈 返回主菜单：/QQEss帮助
Ciallo～(∠・ω< )⌒★"""
    
    await help_msg_command.send(help_text)

@help_group_command.handle()
async def handle_help_group(bot: Bot, event: MessageEvent):
    """显示群组管理功能帮助"""
    help_text = """🏷️ 群组管理功能详细说明
━━━━━━━━━━━━━━━━
📝 加群管理：
  ├ 加群请求推送 - 向配置的目标群推送对应群的加群请求（需配置启用）
  ├ /同意加群请求 - 引用加群请求消息回复（群管理员可用）
  └ /拒绝加群请求 [理由] - 引用加群请求消息回复（群管理员可用）

👥 成员管理：
  ├ /踹 @用户|QQ号 [群号] - 踢出指定用户（SUPERUSER权限）
  ├ /禁言 @用户|QQ号 [群号] 时间 - 禁言指定用户（SUPERUSER权限）
  ├ /解禁 @用户|QQ号 [群号] - 解除禁言指定用户（SUPERUSER权限）
  ├ /全群禁言 - 开启全群禁言（SUPERUSER权限）
  └ /全群解禁 - 关闭全群禁言（SUPERUSER权限）

👑 权限管理：
  ├ /设置管理员 @用户|QQ号 [群号] - 设置群管理员（SUPERUSER权限）
  ├ /取消管理员 @用户|QQ号 [群号] - 取消群管理员（SUPERUSER权限）
  ├ /设置头衔 @用户|QQ号 头衔名 - 设置群头衔（SUPERUSER权限，需群主）
  └ /取消头衔 @用户|QQ号 - 取消群头衔（SUPERUSER权限，需群主）

🚪 群聊管理：
  └ /退群 群号 - 退出指定群聊（SUPERUSER权限）

� 使用说明：
  • 大部分功能仅SUPERUSER可用
  • 头衔设置需要机器人为群主
  • 支持@用户或直接输入QQ号
  • 私聊中使用需要提供群号参数
━━━━━━━━━━━━━━━━
👈 返回主菜单：/QQEss帮助
Ciallo～(∠・ω< )⌒★"""

    await help_group_command.send(help_text)

@help_status_command.handle()
async def handle_help_status(bot: Bot, event: MessageEvent):
    """显示状态设置功能帮助"""
    help_text = """🔧 状态设置功能详细说明
━━━━━━━━━━━━━━━━
📋 基础用法：
  ├ /状态设置 - 查看基础状态
  ├ /状态设置 基础 - 基础状态
  ├ /状态设置 娱乐 - 娱乐状态
  ├ /状态设置 学习工作 - 学习工作状态  
  ├ /状态设置 生活 - 生活状态
  ├ /状态设置 情绪 - 情绪状态
  ├ /状态设置 特殊 - 特殊状态
  └ /状态设置 其他 - 其他状态

⚡ 高级用法：
  ├ /状态设置 电量 - 电量状态说明
  ├ /状态设置 50 [1-100] - 设置电量
  ├ /状态设置 数字 - 用编号设置状态
  └ /状态设置 状态名 - 用名称设置状态

💡 使用说明：
  • 支持40+种个性状态，分类查看更方便
  • 可按分类浏览或直接输入状态名
  • 支持设置电量状态（1-100）
  • 支持数字编号快速设置
━━━━━━━━━━━━━━━━
👈 返回主菜单：/QQEss帮助
Ciallo～(∠・ω< )⌒★"""
    
    await help_status_command.send(help_text)