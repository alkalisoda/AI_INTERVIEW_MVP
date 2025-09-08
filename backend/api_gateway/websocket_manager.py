"""
WebSocket Connection Manager for AI Interview System

This module handles WebSocket connections, message routing, and connection lifecycle management.
Supports long-lived connections for real-time interview interactions.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from .models import (
    WebSocketMessage, WebSocketMessageType, ConnectionInfo, ConnectionStats,
    ConnectMessage, TextInputMessage, AudioInputMessage, ConnectedMessage,
    AIResponseMessage, TranscriptionMessage, ErrorMessage, StatusMessage,
    PingMessage, PongMessage
)
from core.utils import InterviewSession, ResponseFormatter

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    WebSocket连接管理器
    负责管理所有WebSocket连接的生命周期，消息路由和状态跟踪
    """
    
    def __init__(self):
        # 活跃的WebSocket连接
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 连接信息存储
        self.connection_info: Dict[str, ConnectionInfo] = {}
        
        # 面试会话存储（与HTTP API共享）
        self.interview_sessions: Dict[str, InterviewSession] = {}
        
        # 统计信息
        self.stats = ConnectionStats(
            total_connections=0,
            active_connections=0,
            messages_sent=0,
            messages_received=0,
            errors_count=0,
            uptime_seconds=0.0
        )
        
        # 启动时间
        self.start_time = datetime.now()
        
        # 心跳任务
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        logger.info("WebSocket Connection Manager initialized")
    
    async def connect(self, websocket: WebSocket, session_id: str = None) -> str:
        """
        建立WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            session_id: 可选的Session ID，如果不提供将自动生成
            
        Returns:
            str: 分配的Session ID
        """
        # 生成或使用提供的session_id
        if not session_id:
            session_id = str(uuid.uuid4())
        
        try:
            # 接受WebSocket连接
            await websocket.accept()
            
            # 存储连接
            self.active_connections[session_id] = websocket
            
            # 创建连接信息
            client_address = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
            self.connection_info[session_id] = ConnectionInfo(
                session_id=session_id,
                client_address=client_address,
                connected_at=datetime.now(),
                last_activity=datetime.now(),
                is_active=True
            )
            
            # 创建或获取面试会话
            if session_id not in self.interview_sessions:
                self.interview_sessions[session_id] = InterviewSession(session_id)
            
            # 更新统计
            self.stats.total_connections += 1
            self.stats.active_connections = len(self.active_connections)
            
            logger.info(f"WebSocket connected: {session_id} from {client_address}")
            
            # 发送连接确认消息
            await self.send_message(session_id, ConnectedMessage(
                session_id=session_id,
                data={
                    "status": "connected",
                    "server_info": {"version": "2.0.0"},
                    "session_id": session_id
                }
            ))
            
            # 启动心跳检查（如果还没有启动）
            if not self.heartbeat_task:
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {e}")
            await self._cleanup_connection(session_id)
            raise
    
    async def disconnect(self, session_id: str, reason: str = "client_disconnect"):
        """
        断开WebSocket连接
        
        Args:
            session_id: Session ID
            reason: 断开原因
        """
        logger.info(f"Disconnecting WebSocket: {session_id}, reason: {reason}")
        await self._cleanup_connection(session_id)
    
    async def send_message(self, session_id: str, message: WebSocketMessage) -> bool:
        """
        向指定会话发送消息
        
        Args:
            session_id: 目标Session ID
            message: 要发送的消息
            
        Returns:
            bool: 是否发送成功
        """
        if session_id not in self.active_connections:
            logger.warning(f"Attempted to send message to non-existent connection: {session_id}")
            return False
        
        websocket = self.active_connections[session_id]
        
        try:
            # 序列化消息
            message_json = message.model_dump_json()
            
            # 发送消息
            await websocket.send_text(message_json)
            
            # 更新统计和活动时间
            self.stats.messages_sent += 1
            if session_id in self.connection_info:
                self.connection_info[session_id].last_activity = datetime.now()
            
            logger.debug(f"Message sent to {session_id}: {message.type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {session_id}: {e}")
            self.stats.errors_count += 1
            # 连接可能已断开，清理连接
            await self._cleanup_connection(session_id)
            return False
    
    async def broadcast_message(self, message: WebSocketMessage, exclude_sessions: Set[str] = None):
        """
        广播消息到所有连接（可选择排除某些会话）
        
        Args:
            message: 要广播的消息
            exclude_sessions: 要排除的Session ID集合
        """
        exclude_sessions = exclude_sessions or set()
        
        tasks = []
        for session_id in self.active_connections:
            if session_id not in exclude_sessions:
                tasks.append(self.send_message(session_id, message))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful = sum(1 for r in results if r is True)
            logger.info(f"Broadcast completed: {successful}/{len(tasks)} successful")
    
    async def handle_message(self, session_id: str, raw_message: str, ai_coordinator) -> Optional[WebSocketMessage]:
        """
        处理接收到的WebSocket消息
        
        Args:
            session_id: 发送者Session ID
            raw_message: 原始消息字符串
            ai_coordinator: AI协调器实例
            
        Returns:
            Optional[WebSocketMessage]: 响应消息（如果有）
        """
        try:
            # 更新统计和活动时间
            self.stats.messages_received += 1
            if session_id in self.connection_info:
                self.connection_info[session_id].last_activity = datetime.now()
            
            # 解析消息
            message_data = json.loads(raw_message)
            message_type = message_data.get("type")
            
            logger.debug(f"Received message from {session_id}: {message_type}")
            
            # 路由消息到相应的处理器
            if message_type == WebSocketMessageType.PING:
                return await self._handle_ping(session_id, message_data)
            
            elif message_type == WebSocketMessageType.TEXT_INPUT:
                return await self._handle_text_input(session_id, message_data, ai_coordinator)
            
            elif message_type == WebSocketMessageType.AUDIO_INPUT:
                return await self._handle_audio_input(session_id, message_data, ai_coordinator)
            
            elif message_type == WebSocketMessageType.CONNECT:
                return await self._handle_connect(session_id, message_data)
            
            elif message_type == WebSocketMessageType.DISCONNECT:
                await self.disconnect(session_id, "client_requested")
                return None
            
            else:
                logger.warning(f"Unknown message type from {session_id}: {message_type}")
                return ErrorMessage(
                    session_id=session_id,
                    data={
                        "error": "unknown_message_type",
                        "message": f"Unknown message type: {message_type}",
                        "received_type": message_type
                    }
                )
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {session_id}: {e}")
            self.stats.errors_count += 1
            return ErrorMessage(
                session_id=session_id,
                data={
                    "error": "invalid_json",
                    "message": "Invalid JSON format",
                    "details": str(e)
                }
            )
        
        except ValidationError as e:
            logger.error(f"Message validation error from {session_id}: {e}")
            self.stats.errors_count += 1
            return ErrorMessage(
                session_id=session_id,
                data={
                    "error": "validation_error",
                    "message": "Message validation failed",
                    "details": str(e)
                }
            )
        
        except Exception as e:
            logger.error(f"Error handling message from {session_id}: {e}")
            self.stats.errors_count += 1
            return ErrorMessage(
                session_id=session_id,
                data={
                    "error": "processing_error",
                    "message": "Failed to process message",
                    "details": str(e)
                }
            )
    
    async def _handle_ping(self, session_id: str, message_data: dict) -> PongMessage:
        """处理心跳ping消息"""
        return PongMessage(
            session_id=session_id,
            data={"timestamp": datetime.now().isoformat()}
        )
    
    async def _handle_connect(self, session_id: str, message_data: dict) -> StatusMessage:
        """处理连接配置消息"""
        try:
            connect_msg = ConnectMessage(**message_data)
            
            # 更新连接配置
            if session_id in self.connection_info:
                self.connection_info[session_id].interview_style = connect_msg.data.get("interview_style", "formal")
            
            return StatusMessage(
                session_id=session_id,
                data={
                    "status": "configuration_updated",
                    "interview_style": connect_msg.data.get("interview_style", "formal")
                }
            )
        
        except Exception as e:
            logger.error(f"Error handling connect message: {e}")
            return ErrorMessage(
                session_id=session_id,
                data={
                    "error": "connect_error",
                    "message": "Failed to process connect message",
                    "details": str(e)
                }
            )
    
    async def _handle_text_input(self, session_id: str, message_data: dict, ai_coordinator) -> AIResponseMessage:
        """处理文本输入消息"""
        try:
            text_msg = TextInputMessage(**message_data)
            
            # 获取面试会话
            session = self.interview_sessions.get(session_id)
            if not session:
                raise ValueError("Interview session not found")
            
            # 准备输入数据
            input_data = {
                "text": text_msg.get_text(),
                "context": text_msg.get_context() or session.get_context(),
                "original_question": "",  # 可以从会话中获取
                "interview_style": self.connection_info[session_id].interview_style
            }
            
            # 调用AI协调器处理
            result = await ai_coordinator.process_unified_input(
                input_data=input_data,
                session_id=session_id
            )
            
            # 更新会话记录
            if result.get("success", True):
                session.add_ai_interaction(
                    input_type=result["input_type"],
                    user_input=result["user_input"],
                    ai_response=result["ai_response"],
                    processing_time=result.get("processing_time", 0.0),
                    strategy_used=result.get("strategy_used", "unknown"),
                    transcription_info=result.get("transcription_info")
                )
            
            return AIResponseMessage(
                session_id=session_id,
                data={
                    "user_input": result["user_input"],
                    "ai_response": result["ai_response"],
                    "response_type": result.get("response_type", "question"),
                    "strategy_used": result.get("strategy_used", "unknown"),
                    "focus_area": result.get("focus_area", "general"),
                    "confidence": result.get("confidence", 0.5),
                    "processing_time": result.get("processing_time", 0.0),
                    "success": result.get("success", True)
                }
            )
        
        except Exception as e:
            logger.error(f"Error handling text input: {e}")
            return ErrorMessage(
                session_id=session_id,
                data={
                    "error": "text_processing_error",
                    "message": "Failed to process text input",
                    "details": str(e)
                }
            )
    
    async def _handle_audio_input(self, session_id: str, message_data: dict, ai_coordinator) -> AIResponseMessage:
        """处理音频输入消息"""
        try:
            audio_msg = AudioInputMessage(**message_data)
            
            # 获取音频数据
            audio_data = audio_msg.get_audio_data()
            if not audio_data:
                raise ValueError("No audio data provided")
            
            # 获取面试会话
            session = self.interview_sessions.get(session_id)
            if not session:
                raise ValueError("Interview session not found")
            
            # 准备输入数据
            input_data = {
                "audio_content": audio_data,
                "audio_format": audio_msg.get_audio_format(),
                "context": audio_msg.get_context() or session.get_context(),
                "original_question": "",  # 可以从会话中获取
                "interview_style": self.connection_info[session_id].interview_style
            }
            
            # 调用AI协调器处理
            result = await ai_coordinator.process_unified_input(
                input_data=input_data,
                session_id=session_id
            )
            
            # 更新会话记录
            if result.get("success", True):
                session.add_ai_interaction(
                    input_type=result["input_type"],
                    user_input=result["user_input"],
                    ai_response=result["ai_response"],
                    processing_time=result.get("processing_time", 0.0),
                    strategy_used=result.get("strategy_used", "unknown"),
                    transcription_info=result.get("transcription_info")
                )
            
            return AIResponseMessage(
                session_id=session_id,
                data={
                    "user_input": result["user_input"],
                    "ai_response": result["ai_response"],
                    "response_type": result.get("response_type", "question"),
                    "strategy_used": result.get("strategy_used", "unknown"),
                    "focus_area": result.get("focus_area", "general"),
                    "confidence": result.get("confidence", 0.5),
                    "processing_time": result.get("processing_time", 0.0),
                    "transcription_info": result.get("transcription_info"),
                    "success": result.get("success", True)
                }
            )
        
        except Exception as e:
            logger.error(f"Error handling audio input: {e}")
            return ErrorMessage(
                session_id=session_id,
                data={
                    "error": "audio_processing_error",
                    "message": "Failed to process audio input",
                    "details": str(e)
                }
            )
    
    async def _cleanup_connection(self, session_id: str):
        """清理连接相关资源"""
        try:
            # 关闭WebSocket连接
            if session_id in self.active_connections:
                websocket = self.active_connections[session_id]
                try:
                    await websocket.close()
                except:
                    pass  # 连接可能已经关闭
                del self.active_connections[session_id]
            
            # 更新连接信息
            if session_id in self.connection_info:
                self.connection_info[session_id].is_active = False
                # 注意：不删除connection_info，保留用于统计和调试
            
            # 注意：不删除interview_sessions，保持会话记忆
            # 这样即使连接断开，会话数据仍然保留
            
            # 更新统计
            self.stats.active_connections = len(self.active_connections)
            
            logger.info(f"Connection cleaned up: {session_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up connection {session_id}: {e}")
    
    async def _heartbeat_loop(self):
        """心跳检查循环"""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次
                
                current_time = datetime.now()
                inactive_sessions = []
                
                for session_id, info in self.connection_info.items():
                    if info.is_active:
                        # 检查是否超过5分钟没有活动
                        inactive_duration = (current_time - info.last_activity).total_seconds()
                        if inactive_duration > 300:  # 5分钟
                            inactive_sessions.append(session_id)
                
                # 清理不活跃的连接
                for session_id in inactive_sessions:
                    logger.info(f"Cleaning up inactive connection: {session_id}")
                    await self._cleanup_connection(session_id)
                
                # 更新运行时间统计
                self.stats.uptime_seconds = (current_time - self.start_time).total_seconds()
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    def get_connection_stats(self) -> ConnectionStats:
        """获取连接统计信息"""
        current_time = datetime.now()
        self.stats.uptime_seconds = (current_time - self.start_time).total_seconds()
        self.stats.active_connections = len(self.active_connections)
        return self.stats
    
    def get_active_sessions(self) -> List[str]:
        """获取所有活跃Session ID列表"""
        return list(self.active_connections.keys())
    
    def get_session_info(self, session_id: str) -> Optional[ConnectionInfo]:
        """获取指定会话的连接信息"""
        return self.connection_info.get(session_id)
    
    def is_session_active(self, session_id: str) -> bool:
        """检查会话是否活跃"""
        return session_id in self.active_connections

# 全局连接管理器实例
connection_manager = ConnectionManager()
