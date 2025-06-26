import json
import os
import asyncio
import aiohttp
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Union
from pathlib import Path

from nonebot import on_command, get_bot, get_plugin_config, get_driver
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.message import event_postprocessor
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.message import Message, MessageSegment

from .config import Config

# 获取配置
config = get_plugin_config(Config)

# 存储等待状态的用户
waiting_users: Dict[str, Dict] = {}

class LexiconManager:
    """词库管理器"""
    
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.ensure_data_dir()
    
    def ensure_data_dir(self):
        """确保数据目录存在"""
        self.data_path.mkdir(parents=True, exist_ok=True)        # 确保图片和语音目录存在
        (self.data_path / "pic").mkdir(exist_ok=True)
        (self.data_path / "voice").mkdir(exist_ok=True)
    
    def get_group_file_path(self, group_id: int) -> Path:
        """获取群词库文件路径"""
        return self.data_path / f"group{group_id}.json"
    
    def get_user_file_path(self, user_id: int) -> Path:
        """获取用户词库文件路径"""
        return self.data_path / f"uin{user_id}.json"
    
    def get_global_file_path(self) -> Path:
        """获取全局词库文件路径"""
        return self.data_path / "global.json"
    
    def get_blacklist_file_path(self) -> Path:
        """获取黑名单文件路径"""
        return self.data_path / "lexiconblacklist.json"
    
    async def download_media_file(self, url: str, file_type: str) -> Optional[str]:
        """下载媒体文件并返回本地文件名"""
        try:
            # 生成文件名
            url_hash = hashlib.md5(url.encode()).hexdigest()
            timestamp = int(datetime.now().timestamp())
            
            if file_type == "image":
                # 直接使用通用扩展名
                filename = f"{timestamp}_{url_hash}.jpg"
                save_dir = self.data_path / "pic"
            elif file_type == "voice":
                # 直接使用通用扩展名
                filename = f"{timestamp}_{url_hash}.silk"
                save_dir = self.data_path / "voice"
            else:
                return None
            
            # 确保目录存在
            save_dir.mkdir(parents=True, exist_ok=True)
            file_path = save_dir / filename
            
            logger.info(f"准备下载媒体文件: {url} -> {file_path}")
              # 检查URL是否为本地文件路径
            if url.startswith('file://') or Path(url).exists():
                # 本地文件，直接复制
                source_path = Path(url.replace('file://', '')) if url.startswith('file://') else Path(url)
                if source_path.exists():
                    import shutil
                    shutil.copy2(source_path, file_path)
                    logger.info(f"成功复制本地媒体文件: {filename}")
                    return filename
                else:
                    logger.error(f"本地文件不存在: {source_path}")
                    return None
            
            # 处理 base64 编码的文件
            if url.startswith('base64://'):
                import base64
                base64_data = url.replace('base64://', '')
                try:
                    file_data = base64.b64decode(base64_data)
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                    logger.info(f"成功保存base64媒体文件: {filename}")
                    return filename
                except Exception as e:
                    logger.error(f"保存base64文件失败: {e}")
                    return None
            
            # 网络文件，下载
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(file_path, 'wb') as f:
                            f.write(content)
                        logger.info(f"成功下载媒体文件: {filename}")
                        return filename
                    else:
                        logger.error(f"下载媒体文件失败，状态码: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"下载媒体文件时出错: {e}")
            return None
    
    def get_media_file_path(self, filename: str, file_type: str) -> Path:
        """获取媒体文件的完整路径"""
        if file_type == "image":
            return self.data_path / "pic" / filename
        elif file_type == "voice":
            return self.data_path / "voice" / filename
        else:
            return self.data_path / filename
    
    async def parse_message_content(self, message: Message) -> Dict:
        """解析消息内容，提取文本、图片和语音"""
        content = {
            "type": "text",
            "text": "",
            "media_files": []
        }
        
        text_parts = []
        has_media = False
        
        for segment in message:
            if segment.type == "text":
                text_parts.append(segment.data.get("text", ""))
            elif segment.type == "image":
                has_media = True
                url = segment.data.get("url") or segment.data.get("file")
                if url:
                    filename = await self.download_media_file(url, "image")
                    if filename:
                        content["media_files"].append({
                            "type": "image",
                            "filename": filename
                        })
            elif segment.type == "record":
                has_media = True
                url = segment.data.get("url") or segment.data.get("file")
                if url:
                    filename = await self.download_media_file(url, "voice")
                    if filename:
                        content["media_files"].append({
                            "type": "voice",
                            "filename": filename
                        })
        
        content["text"] = "".join(text_parts).strip()
        if has_media:
            content["type"] = "mixed" if content["text"] else "media"
        
        return content
    
    def load_data(self, file_path: Path) -> List[Dict]:
        """加载词库数据"""
        if not file_path.exists():
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载词库文件失败: {file_path}, 错误: {e}")
            return []
    
    def save_data(self, file_path: Path, data: List[Dict]):
        """保存词库数据"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存词库文件失败: {file_path}, 错误: {e}")
    
    def load_blacklist(self) -> List[int]:
        """加载黑名单"""
        file_path = self.get_blacklist_file_path()
        if not file_path.exists():
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载黑名单文件失败: {e}")
            return []
    
    def save_blacklist(self, blacklist: List[int]):
        """保存黑名单"""
        file_path = self.get_blacklist_file_path()
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(blacklist, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存黑名单文件失败: {e}")
    
    def is_blacklisted(self, user_id: int) -> bool:
        """检查用户是否被拉黑"""
        blacklist = self.load_blacklist()
        return user_id in blacklist
    
    def add_to_blacklist(self, user_id: int):
        """添加用户到黑名单"""
        blacklist = self.load_blacklist()
        if user_id not in blacklist:
            blacklist.append(user_id)
            self.save_blacklist(blacklist)
    
    async def add_lexicon(self, file_path: Path, keyword: str, reply_content: Union[str, Dict], user_id: int, is_group: bool = False):
        """添加词条（支持文本、图片、语音）"""
        data = self.load_data(file_path)
        
        # 处理回复内容
        if isinstance(reply_content, str):
            # 纯文本回复
            reply_data = {
                "type": "text",
                "content": reply_content
            }
        else:
            # 包含媒体的回复
            reply_data = reply_content
        
        # 检查是否已存在相同关键词
        for item in data:
            if item.get("keyword") == keyword:
                # 更新现有词条
                item["reply"] = reply_data
                item["uin"] = str(user_id)
                item["created_at"] = datetime.now().isoformat()
                self.save_data(file_path, data)
                return True
          # 添加新词条
        new_item = {
            "keyword": keyword,
            "reply": reply_data,
            "created_at": datetime.now().isoformat()
        }
        
        if is_group:
            new_item["uin"] = str(user_id)
        
        data.append(new_item)
        self.save_data(file_path, data)
        return True
    
    def delete_lexicon(self, file_path: Path, keyword: str) -> bool:
        """删除词条"""
        data = self.load_data(file_path)
        original_len = len(data)
        data = [item for item in data if item.get("keyword") != keyword]
        
        if len(data) < original_len:
            self.save_data(file_path, data)
            return True
        return False
    
    def search_reply(self, keyword: str, group_id: Optional[int] = None, user_id: Optional[int] = None) -> Optional[Union[str, Dict]]:
        """搜索词条回复"""
        # 优先级：群词库 > 用户词库 > 全局词库
        
        if group_id:
            # 搜索群词库
            group_data = self.load_data(self.get_group_file_path(group_id))
            for item in group_data:
                if item.get("keyword") == keyword:
                    return item.get("reply")
        
        if user_id:
            # 搜索用户词库
            user_data = self.load_data(self.get_user_file_path(user_id))
            for item in user_data:
                if item.get("keyword") == keyword:
                    return item.get("reply")
        
        # 搜索全局词库
        global_data = self.load_data(self.get_global_file_path())
        for item in global_data:
            if item.get("keyword") == keyword:
                return item.get("reply")
        
        return None
    
    async def build_reply_message(self, reply_data: Union[str, Dict]) -> Message:
        """构建回复消息，支持文本、图片、语音"""
        if isinstance(reply_data, str):
            # 向后兼容：纯文本回复
            return Message(reply_data)
        
        if not isinstance(reply_data, dict):
            return Message("回复数据格式错误")
        
        reply_type = reply_data.get("type", "text")
        message = Message()
        
        if reply_type == "text":
            # 纯文本
            content = reply_data.get("content", "")
            if content:
                message += MessageSegment.text(content)
        
        elif reply_type in ["media", "mixed"]:
            # 包含媒体内容            # 添加文本部分（如果有）
            text_content = reply_data.get("content", "")
            if text_content:
                message += MessageSegment.text(text_content)
            
            # 添加媒体文件
            media_files = reply_data.get("media_files", [])
            for media in media_files:
                media_type = media.get("type")
                filename = media.get("filename")
                
                if not filename:
                    continue
                
                if media_type == "image":
                    file_path = self.get_media_file_path(filename, "image")
                    if file_path.exists():
                        # 使用 base64 编码发送图片
                        try:
                            import base64
                            with open(file_path, 'rb') as f:
                                image_data = f.read()
                            base64_data = base64.b64encode(image_data).decode()
                            message += MessageSegment.image(f"base64://{base64_data}")
                        except Exception as e:
                            logger.error(f"读取图片文件失败: {filename}, 错误: {e}")
                    else:
                        logger.warning(f"图片文件不存在: {filename}")
                
                elif media_type == "voice":
                    file_path = self.get_media_file_path(filename, "voice")
                    if file_path.exists():
                        # 使用 base64 编码发送语音
                        try:
                            import base64
                            with open(file_path, 'rb') as f:
                                voice_data = f.read()
                            base64_data = base64.b64encode(voice_data).decode()
                            message += MessageSegment.record(f"base64://{base64_data}")
                        except Exception as e:
                            logger.error(f"读取语音文件失败: {filename}, 错误: {e}")
                    else:
                        logger.warning(f"语音文件不存在: {filename}")
        
        return message if message else Message("回复内容为空")

# 初始化词库管理器
lexicon_manager = LexiconManager(os.path.join(config.data_path, "lexicon"))

# 词条添加命令
add_lexicon = on_command("添加词条", priority=5, block=True)
add_global_lexicon = on_command("全局添加词条", priority=5, block=True, permission=SUPERUSER)
delete_lexicon_cmd = on_command("删除词条", priority=5, block=True)
delete_global_lexicon = on_command("全局删除词条", priority=5, block=True, permission=SUPERUSER)
add_blacklist = on_command("添加词条黑名单", priority=5, block=True, permission=SUPERUSER)
view_lexicon = on_command("查看词库", priority=5, block=True)
view_global_lexicon = on_command("查看全局词库", priority=5, block=True, permission=SUPERUSER)
lexicon_help = on_command("词库帮助", aliases={"词条帮助"}, priority=10, block=True)

# 使用事件后处理器来处理词条触发
@event_postprocessor
async def lexicon_postprocessor(
    bot: Bot,
    event: MessageEvent,
):
    """词条后处理器"""
    # 屏蔽机器人自己发的消息
    if event.user_id == int(bot.self_id):
        return
    
    user_id = event.user_id
    message_text = event.message.extract_plain_text().strip()
    
    # 确定上下文ID
    if isinstance(event, GroupMessageEvent):
        context_id = f"group_{event.group_id}_{user_id}"
        global_context_id = f"global_group_{event.group_id}_{user_id}"
    else:
        context_id = f"user_{user_id}"
        global_context_id = f"global_user_{user_id}"    # 处理等待状态
    if context_id in waiting_users or global_context_id in waiting_users:
        wait_info = waiting_users.get(context_id) or waiting_users.get(global_context_id)
        current_context_id = context_id if context_id in waiting_users else global_context_id
        
        if wait_info and wait_info["user_id"] == user_id:  # 只处理对应用户的消息
            # 检查是否刚刚设置等待状态（避免处理提示消息本身）
            if "start_time" in wait_info:
                time_diff = (datetime.now() - wait_info["start_time"]).total_seconds()
                if time_diff < 2:  # 2秒内的消息忽略，避免处理提示消息
                    return
              # 检查取消命令
            if message_text == "/我不写了":
                # 撤回提示消息
                try:
                    if "message_id" in wait_info:
                        await bot.delete_msg(message_id=wait_info["message_id"])
                except:
                    pass
                
                del waiting_users[current_context_id]
                await bot.send(event, "操作已取消")
                return
            
            # 处理等待输入
            if wait_info["step"] == "keyword":
                # 等待关键词
                keyword = message_text
                waiting_users[current_context_id]["keyword"] = keyword
                waiting_users[current_context_id]["step"] = "reply"
                waiting_users[current_context_id]["start_time"] = datetime.now()  # 重置开始时间
                
                # 延迟一下再撤回上一条提示消息，避免太快撤回
                await asyncio.sleep(0.5)
                try:
                    if "message_id" in wait_info:
                        await bot.delete_msg(message_id=wait_info["message_id"])
                except:
                    pass
                  # 发送新提示
                is_global = wait_info.get("is_global", False)
                msg = await bot.send(event, f"下一步:请在一分钟内写出回复词(可以是文本、图片或语音)\n或者说:/我不写了 取消操作")
                waiting_users[current_context_id]["message_id"] = msg["message_id"]
                  # 重新设置超时任务
                asyncio.create_task(timeout_task(current_context_id, config.lexicon_timeout))
                return
                
            elif wait_info["step"] == "reply":
                # 等待回复词（支持文本、图片、语音）
                reply_content = await lexicon_manager.parse_message_content(event.message)
                keyword = wait_info["keyword"]
                file_path = wait_info["file_path"]
                is_group = wait_info["is_group"]
                
                # 延迟一下再撤回提示消息
                await asyncio.sleep(0.5)
                try:
                    if "message_id" in wait_info:
                        await bot.delete_msg(message_id=wait_info["message_id"])
                except:
                    pass
                
                # 添加词条
                await lexicon_manager.add_lexicon(file_path, keyword, reply_content, user_id, is_group)
                del waiting_users[current_context_id]
                await bot.send(event, "添加成功！")
                return
      # 只有在没有等待状态时才进行词条触发
    # 并且不是命令消息时才检查词条
    if (not message_text.startswith('/') and 
        not lexicon_manager.is_blacklisted(user_id) and
        not (context_id in waiting_users or global_context_id in waiting_users)):
        
        group_id = event.group_id if isinstance(event, GroupMessageEvent) else None
        reply = lexicon_manager.search_reply(message_text, group_id, user_id)
        
        if reply:
            # 构建并发送回复消息
            reply_message = await lexicon_manager.build_reply_message(reply)
            await bot.send(event, reply_message)

@add_lexicon.handle()
async def handle_add_lexicon(bot: Bot, event: MessageEvent, matcher: Matcher, args: Message = CommandArg()):
    """处理添加词条命令"""
    user_id = event.user_id
    
    # 检查黑名单
    if lexicon_manager.is_blacklisted(user_id):
        return  # 静默处理，不发送任何消息
    
    args_text = args.extract_plain_text().strip()
    
    # 确定存储路径
    if isinstance(event, GroupMessageEvent):
        file_path = lexicon_manager.get_group_file_path(event.group_id)
        context_id = f"group_{event.group_id}_{user_id}"
        is_group = True
    else:
        file_path = lexicon_manager.get_user_file_path(user_id)
        context_id = f"user_{user_id}"
        is_group = False
    
    if not args_text:
        # /添加词条 - 等待关键词
        waiting_users[context_id] = {
            "step": "keyword",
            "user_id": user_id,
            "file_path": file_path,
            "is_group": is_group,
            "start_time": datetime.now()
        }
        msg = await matcher.send("你已触发添加词条功能(仅本群)\n请在1分钟内写出关键词\n或者说:/我不写了 取消操作")
        waiting_users[context_id]["message_id"] = msg["message_id"]
        
        # 设置超时任务
        asyncio.create_task(timeout_task(context_id, config.lexicon_timeout))
        
    else:
        parts = args_text.split(None, 1)
        if len(parts) == 1:
            # /添加词条 关键词 - 等待回复词
            keyword = parts[0]
            waiting_users[context_id] = {
                "step": "reply",
                "keyword": keyword,
                "user_id": user_id,
                "file_path": file_path,
                "is_group": is_group,
                "start_time": datetime.now()
            }
            msg = await matcher.send("你已触发添加词条功能(仅本群)\n请在1分钟内写出回复消息(可以是文本、图片或语音)\n或者说:/我不写了 取消操作")
            waiting_users[context_id]["message_id"] = msg["message_id"]
              # 设置超时任务
            asyncio.create_task(timeout_task(context_id, config.lexicon_timeout))
            
        elif len(parts) == 2:
            # /添加词条 关键词 回复词 - 直接添加
            keyword, reply = parts
            await lexicon_manager.add_lexicon(file_path, keyword, reply, user_id, is_group)
            await matcher.finish("添加成功！")

@add_global_lexicon.handle()
async def handle_add_global_lexicon(bot: Bot, event: MessageEvent, matcher: Matcher, args: Message = CommandArg()):
    """处理全局添加词条命令"""
    user_id = event.user_id
    
    # 检查黑名单
    if lexicon_manager.is_blacklisted(user_id):
        return  # 静默处理，不发送任何消息
    
    args_text = args.extract_plain_text().strip()
    file_path = lexicon_manager.get_global_file_path()
    
    if isinstance(event, GroupMessageEvent):
        context_id = f"global_group_{event.group_id}_{user_id}"
    else:
        context_id = f"global_user_{user_id}"
    
    if not args_text:
        # /全局添加词条 - 等待关键词
        waiting_users[context_id] = {
            "step": "keyword",
            "user_id": user_id,
            "file_path": file_path,
            "is_group": False,
            "is_global": True,
            "start_time": datetime.now()
        }
        msg = await matcher.send("你已触发添加词条功能(全局模式)\n请在一分钟内写出关键词\n或者说:/我不写了 取消操作")
        waiting_users[context_id]["message_id"] = msg["message_id"]
        
        # 设置超时任务
        asyncio.create_task(timeout_task(context_id, config.lexicon_timeout))
        
    else:
        parts = args_text.split(None, 1)
        if len(parts) == 1:
            # /全局添加词条 关键词 - 等待回复词
            keyword = parts[0]
            waiting_users[context_id] = {
                "step": "reply",
                "keyword": keyword,
                "user_id": user_id,
                "file_path": file_path,
                "is_group": False,
                "is_global": True,
                "start_time": datetime.now()
            }
            msg = await matcher.send("你已触发添加词条功能(全局模式)\n请在1分钟内写出回复消息(可以是文本、图片或语音)\n或者说:/我不写了 取消操作")
            waiting_users[context_id]["message_id"] = msg["message_id"]
              # 设置超时任务
            asyncio.create_task(timeout_task(context_id, config.lexicon_timeout))
            
        elif len(parts) == 2:
            # /全局添加词条 关键词 回复词 - 直接添加
            keyword, reply = parts
            await lexicon_manager.add_lexicon(file_path, keyword, reply, user_id, False)
            await matcher.finish("添加成功！")

@delete_lexicon_cmd.handle()
async def handle_delete_lexicon(bot: Bot, event: MessageEvent, matcher: Matcher, args: Message = CommandArg()):
    """处理删除词条命令"""
    user_id = event.user_id
    
    # 检查黑名单
    if lexicon_manager.is_blacklisted(user_id):
        return  # 静默处理，不发送任何消息
    
    keyword = args.extract_plain_text().strip()
    if not keyword:
        await matcher.finish("请输入要删除的关键词")
    
    # 确定删除路径
    if isinstance(event, GroupMessageEvent):
        file_path = lexicon_manager.get_group_file_path(event.group_id)
    else:
        file_path = lexicon_manager.get_user_file_path(user_id)
    
    if lexicon_manager.delete_lexicon(file_path, keyword):
        await matcher.finish("删除成功！")
    else:
        await matcher.finish("未找到该关键词")

@delete_global_lexicon.handle()
async def handle_delete_global_lexicon(bot: Bot, event: MessageEvent, matcher: Matcher, args: Message = CommandArg()):
    """处理全局删除词条命令"""
    user_id = event.user_id
    
    keyword = args.extract_plain_text().strip()
    if not keyword:
        await matcher.finish("请输入要删除的关键词")
    
    file_path = lexicon_manager.get_global_file_path()
    
    if lexicon_manager.delete_lexicon(file_path, keyword):
        await matcher.finish("删除成功！")
    else:
        await matcher.finish("未找到该关键词")

@add_blacklist.handle()
async def handle_add_blacklist(bot: Bot, event: MessageEvent, matcher: Matcher, args: Message = CommandArg()):
    """处理添加词条黑名单命令"""
    user_id = event.user_id
    
    target_qq = args.extract_plain_text().strip()
    if not target_qq.isdigit():
        await matcher.finish("请输入正确的QQ号")
    
    target_qq = int(target_qq)
    lexicon_manager.add_to_blacklist(target_qq)
    await matcher.finish(f"已将 {target_qq} 添加到词条黑名单")

@view_lexicon.handle()
async def handle_view_lexicon(bot: Bot, event: MessageEvent, matcher: Matcher):
    """处理查看词库命令"""
    user_id = event.user_id
      # 检查黑名单
    if lexicon_manager.is_blacklisted(user_id):
        return  # 静默处理，不发送任何消息
    
    # 确定词库路径
    if isinstance(event, GroupMessageEvent):
        file_path = lexicon_manager.get_group_file_path(event.group_id)
        scope_text = f"群 {event.group_id}"
    else:
        file_path = lexicon_manager.get_user_file_path(user_id)
        scope_text = "个人"
      # 加载词库数据
    data = lexicon_manager.load_data(file_path)
    
    if not data:
        await matcher.finish(f"📚 {scope_text}词库为空")
    
    try:
        # 构建合并消息 - 每个词条两条消息
        messages = []
        
        for i, item in enumerate(data, 1):
            keyword = item.get("keyword", "未知")
            reply_data = item.get("reply", {})
            
            # 第一条消息：关键词（带序号）
            keyword_text = f"{i}. {keyword}"
            messages.append(MessageSegment.node_custom(
                user_id=user_id,
                nickname="柚子厨",
                content=Message(keyword_text)
            ))
            
            # 第二条消息：回复内容
            if isinstance(reply_data, str):
                # 兼容旧格式的纯文本回复
                reply_content = reply_data
            elif isinstance(reply_data, dict):
                reply_type = reply_data.get("type", "text")
                if reply_type == "text":
                    reply_content = reply_data.get("content", "")
                elif reply_type == "media":
                    media_files = reply_data.get("media_files", [])
                    media_count = len(media_files)
                    media_types = [m.get("type", "未知") for m in media_files]
                    type_text = "、".join(set(media_types))
                    reply_content = f"[媒体文件: {type_text} ({media_count}个)]"
                elif reply_type == "mixed":
                    content = reply_data.get("content", "")
                    media_files = reply_data.get("media_files", [])
                    media_count = len(media_files)
                    reply_content = f"{content} [+{media_count}个媒体文件]"
                else:
                    reply_content = "[未知格式]"
            else:
                reply_content = "[格式错误]"
            
            messages.append(MessageSegment.node_custom(
                user_id=int(bot.self_id),
                nickname="Ciallo～(∠・ω< )⌒★",
                content=Message(reply_content)
            ))
        
        # 发送合并消息
        if isinstance(event, GroupMessageEvent):
            await bot.send_group_forward_msg(
                group_id=event.group_id,
                messages=messages
            )
        else:
            await bot.send_private_forward_msg(
                user_id=user_id,
                messages=messages
            )
        
    except Exception as e:
        logger.error(f"发送词库信息失败: {e}")
        # 发送失败就静默处理，不发送任何消息

@view_global_lexicon.handle()
async def handle_view_global_lexicon(bot: Bot, event: MessageEvent, matcher: Matcher):
    """处理查看全局词库命令"""
    user_id = event.user_id
    
    # 获取全局词库路径
    file_path = lexicon_manager.get_global_file_path()
      # 加载词库数据
    data = lexicon_manager.load_data(file_path)
    
    if not data:
        await matcher.finish("📚 全局词库为空")
    
    try:
        # 构建合并消息 - 每个词条两条消息
        messages = []
        
        for i, item in enumerate(data, 1):
            keyword = item.get("keyword", "未知")
            reply_data = item.get("reply", {})
            
            # 第一条消息：关键词（带序号）
            keyword_text = f"{i}. {keyword}"
            messages.append(MessageSegment.node_custom(
                user_id=user_id,
                nickname="柚子厨",
                content=Message(keyword_text)
            ))
            
            # 第二条消息：回复内容
            if isinstance(reply_data, str):
                # 兼容旧格式的纯文本回复
                reply_content = reply_data
            elif isinstance(reply_data, dict):
                reply_type = reply_data.get("type", "text")
                if reply_type == "text":
                    reply_content = reply_data.get("content", "")
                elif reply_type == "media":
                    media_files = reply_data.get("media_files", [])
                    media_count = len(media_files)
                    media_types = [m.get("type", "未知") for m in media_files]
                    type_text = "、".join(set(media_types))
                    reply_content = f"[媒体文件: {type_text} ({media_count}个)]"
                elif reply_type == "mixed":
                    content = reply_data.get("content", "")
                    media_files = reply_data.get("media_files", [])
                    media_count = len(media_files)
                    reply_content = f"{content} [+{media_count}个媒体文件]"
                else:
                    reply_content = "[未知格式]"
            else:
                reply_content = "[格式错误]"
            
            messages.append(MessageSegment.node_custom(
                user_id=int(bot.self_id),
                nickname="Ciallo～(∠・ω< )⌒★",
                content=Message(reply_content)
            ))
        
        # 发送合并消息
        if isinstance(event, GroupMessageEvent):
            await bot.send_group_forward_msg(
                group_id=event.group_id,
                messages=messages
            )
        else:
            await bot.send_private_forward_msg(
                user_id=user_id,
                messages=messages
            )
        
    except Exception as e:
        logger.error(f"发送全局词库信息失败: {e}")
        # 发送失败就静默处理，不发送任何消息

@lexicon_help.handle()
async def handle_lexicon_help(bot: Bot, event: MessageEvent, matcher: Matcher):
    """显示词库功能帮助"""
    help_text = """📚 词库功能帮助
━━━━━━━━━━━━━━━━
📝 词条管理：
  ├ /添加词条 [关键词] [回复] - 添加群/个人词条
  ├ /全局添加词条 [关键词] [回复] - 添加全局词条(超级用户)
  ├ /删除词条 关键词 - 删除群/个人词条
  └ /全局删除词条 关键词 - 删除全局词条(超级用户)

📋 词库查看：
  ├ /查看词库 - 查看当前群/个人词库(合并消息)
  └ /查看全局词库 - 查看全局词库(超级用户)

🚫 黑名单管理：
  └ /添加词条黑名单 QQ号 - 禁用用户词条功能(超级用户)

💡 使用说明：
  • 支持文本、图片、语音、混合消息
  • 优先级：群词库 > 个人词库 > 全局词库
  • 添加词条支持分步操作和一次性输入
  • 查看词库使用合并消息展示，失败时自动降级
  • 词条触发无需指令头，直接发送关键词即可

🎯 添加示例：
  ├ /添加词条 → 分步引导添加
  ├ /添加词条 你好 → 等待回复内容
  ├ /添加词条 你好 Hello! → 直接添加
  └ 支持图片、语音等多媒体内容

🔍 查看示例：
  • /查看词库 → 显示当前群词库(2条消息)
    1️⃣ 关键词列表(带序号)
    2️⃣ 对应回复内容

⚠️ 注意事项：
  • 全局功能仅超级用户可用
  • 被拉黑用户无法使用词条功能
  • 媒体文件自动下载存储到本地
━━━━━━━━━━━━━━━━
Ciallo～(∠・ω< )⌒★"""
    
    await matcher.finish(help_text)

async def timeout_task(context_id: str, timeout: int):
    """超时任务"""
    await asyncio.sleep(timeout)
    
    if context_id in waiting_users:
        wait_info = waiting_users[context_id]
        
        # 撤回提示消息
        try:
            bot = get_bot()
            if "message_id" in wait_info:
                await bot.delete_msg(message_id=wait_info["message_id"])
        except:
            pass
        
        del waiting_users[context_id]
        logger.info(f"词条添加超时，已清理等待状态: {context_id}")
