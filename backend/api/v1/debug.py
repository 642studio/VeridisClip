"""
调试API接口
用于测试和调试功能
"""

import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import redis.asyncio as redis
from ...core.config import get_redis_url
from ...core.path_utils import get_data_directory
from ...utils.llm_debug import is_llm_debug_enabled

logger = logging.getLogger(__name__)
router = APIRouter()

class PublishMessage(BaseModel):
    """发布消息模型"""
    task_id: str
    progress: int
    step: int = 1
    total: int = 6
    phase: str = "test"
    message: str = "调试消息"
    status: str = "PROGRESS"
    seq: int = 1
    meta: Dict[str, Any] = {}


@router.get("/debug/llm/status")
async def debug_llm_status():
    """调试接口：查看LLM调试开关状态和日志目录"""
    debug_dir = get_data_directory() / "logs" / "llm_debug"
    return {
        "enabled": is_llm_debug_enabled(),
        "debug_dir": str(debug_dir),
        "events_file": str(debug_dir / "events.jsonl"),
        "exists": debug_dir.exists(),
    }


@router.get("/debug/llm/events")
async def debug_llm_events(lines: int = 100):
    """调试接口：读取最近N条LLM调试事件"""
    try:
        debug_dir = get_data_directory() / "logs" / "llm_debug"
        events_file = debug_dir / "events.jsonl"
        if not events_file.exists():
            return {"enabled": is_llm_debug_enabled(), "events": []}

        with open(events_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()

        recent = all_lines[-max(1, min(lines, 1000)):]
        events = []
        for line in recent:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"raw": line})

        return {"enabled": is_llm_debug_enabled(), "events": events}
    except Exception as e:
        logger.error(f"读取LLM调试事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"读取失败: {str(e)}")

@router.post("/debug/publish")
async def debug_publish_message(message: PublishMessage):
    """调试接口：发布进度消息到Redis"""
    try:
        # 连接Redis
        redis_client = redis.from_url(get_redis_url(), decode_responses=True)
        
        # 构建消息
        import time
        full_message = {
            "task_id": message.task_id,
            "progress": message.progress,
            "step": message.step,
            "total": message.total,
            "phase": message.phase,
            "message": message.message,
            "status": message.status,
            "seq": message.seq,
            "ts": time.time(),
            "meta": message.meta
        }
        
        # 发布到Redis
        channel = f"progress:{message.task_id}"
        result = await redis_client.publish(channel, json.dumps(full_message))
        
        await redis_client.aclose()
        
        logger.info(f"调试发布消息: {channel} -> {result} 个订阅者")
        
        return {
            "success": True,
            "channel": channel,
            "subscribers": result,
            "message": full_message
        }
        
    except Exception as e:
        logger.error(f"调试发布消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"发布失败: {str(e)}")

@router.get("/debug/subscriptions")
async def debug_get_subscriptions():
    """调试接口：获取当前订阅状态"""
    try:
        from ...services.websocket_gateway_service import websocket_gateway_service
        
        async with websocket_gateway_service.lock:
            return {
                "success": True,
                "active_channels": len(websocket_gateway_service.channels_ref),
                "channels": dict(websocket_gateway_service.channels_ref),
                "user_subscriptions": dict(websocket_gateway_service.user_subscriptions)
            }
            
    except Exception as e:
        logger.error(f"获取订阅状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@router.get("/debug/redis-info")
async def debug_redis_info():
    """调试接口：获取Redis连接信息"""
    try:
        redis_url = get_redis_url()
        redis_client = redis.from_url(redis_url, decode_responses=True)
        
        # 测试连接
        await redis_client.ping()
        
        # 获取信息
        info = await redis_client.info()
        
        await redis_client.aclose()
        
        return {
            "success": True,
            "redis_url": redis_url,
            "redis_version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory": info.get("used_memory_human")
        }
        
    except Exception as e:
        logger.error(f"获取Redis信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")
