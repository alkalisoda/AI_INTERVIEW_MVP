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
    WebSocket connection manager
    Responsible for managing the lifecycle, message routing and state tracking of all WebSocket connections
    """
    
    def __init__(self):
        # Active WebSocket connections
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Connection information storage
        self.connection_info: Dict[str, ConnectionInfo] = {}
        
        # Interview session storage (shared with HTTP API)
        self.interview_sessions: Dict[str, InterviewSession] = {}
        
        # Statistics
        self.stats = ConnectionStats(
            total_connections=0,
            active_connections=0,
            messages_sent=0,
            messages_received=0,
            errors_count=0,
            uptime_seconds=0.0
        )
        
        # Start time
        self.start_time = datetime.now()
        
        # Heartbeat task
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        logger.info("WebSocket Connection Manager initialized")
    
    async def connect(self, websocket: WebSocket, session_id: str = None) -> str:
        """
        Establish WebSocket connection
        
        Args:
            websocket: WebSocket connection object
            session_id: Optional Session ID, auto-generated if not provided
            
        Returns:
            str: Assigned Session ID
        """
        # Generate or use provided session_id
        if not session_id:
            session_id = str(uuid.uuid4())
        
        try:
            # Accept WebSocket connection
            await websocket.accept()
            
            # Store connection
            self.active_connections[session_id] = websocket
            
            # Create connection info
            client_address = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
            self.connection_info[session_id] = ConnectionInfo(
                session_id=session_id,
                client_address=client_address,
                connected_at=datetime.now(),
                last_activity=datetime.now(),
                is_active=True
            )
            
            # Create or get interview session
            if session_id not in self.interview_sessions:
                self.interview_sessions[session_id] = InterviewSession(session_id)
            
            # Update statistics
            self.stats.total_connections += 1
            self.stats.active_connections = len(self.active_connections)
            
            logger.info(f"WebSocket connected: {session_id} from {client_address}")
            
            # Send connection confirmation message
            await self.send_message(session_id, ConnectedMessage(
                session_id=session_id,
                data={
                    "status": "connected",
                    "server_info": {"version": "2.0.0"},
                    "session_id": session_id
                }
            ))
            
            # Start heartbeat check (if not already started)
            if not self.heartbeat_task:
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {e}")
            await self._cleanup_connection(session_id)
            raise
    
    async def disconnect(self, session_id: str, reason: str = "client_disconnect"):
        """
        Disconnect WebSocket connection
        
        Args:
            session_id: Session ID
            reason: Disconnect reason
        """
        logger.info(f"Disconnecting WebSocket: {session_id}, reason: {reason}")
        await self._cleanup_connection(session_id)
    
    async def send_message(self, session_id: str, message: WebSocketMessage) -> bool:
        """
        Send message to specified session
        
        Args:
            session_id: Target Session ID
            message: Message to send
            
        Returns:
            bool: Whether send was successful
        """
        if session_id not in self.active_connections:
            logger.warning(f"Attempted to send message to non-existent connection: {session_id}")
            return False
        
        websocket = self.active_connections[session_id]
        
        try:
            # Serialize message
            message_json = message.model_dump_json()
            
            # Send message
            await websocket.send_text(message_json)
            
            # Update statistics and activity time
            self.stats.messages_sent += 1
            if session_id in self.connection_info:
                self.connection_info[session_id].last_activity = datetime.now()
            
            logger.debug(f"Message sent to {session_id}: {message.type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {session_id}: {e}")
            self.stats.errors_count += 1
            # Connection may be broken, clean up
            await self._cleanup_connection(session_id)
            return False
    
    async def broadcast_message(self, message: WebSocketMessage, exclude_sessions: Set[str] = None):
        """
        Broadcast message to all connections (optionally excluding certain sessions)
        
        Args:
            message: Message to broadcast
            exclude_sessions: Set of Session IDs to exclude
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
        Handle received WebSocket message
        
        Args:
            session_id: Sender Session ID
            raw_message: Raw message string
            ai_coordinator: AI coordinator instance
            
        Returns:
            Optional[WebSocketMessage]: Response message (if any)
        """
        try:
            # Update statistics and activity time
            self.stats.messages_received += 1
            if session_id in self.connection_info:
                self.connection_info[session_id].last_activity = datetime.now()
            
            # Parse message
            message_data = json.loads(raw_message)
            message_type = message_data.get("type")
            
            logger.debug(f"Received message from {session_id}: {message_type}")
            
            # Route message to appropriate handler
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
        """Handle heartbeat ping message"""
        return PongMessage(
            session_id=session_id,
            data={"timestamp": datetime.now().isoformat()}
        )
    
    async def _handle_connect(self, session_id: str, message_data: dict) -> StatusMessage:
        """Handle connection configuration message"""
        try:
            connect_msg = ConnectMessage(**message_data)
            
            # Update connection configuration
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
        """Handle text input message"""
        try:
            text_msg = TextInputMessage(**message_data)
            
            # Get interview session
            session = self.interview_sessions.get(session_id)
            if not session:
                raise ValueError("Interview session not found")
            
            # Prepare input data
            input_data = {
                "text": text_msg.get_text(),
                "context": text_msg.get_context() or session.get_context(),
                "original_question": "",  # Can be obtained from session
                "interview_style": self.connection_info[session_id].interview_style
            }
            
            # Call AI coordinator for processing
            result = await ai_coordinator.process_unified_input(
                input_data=input_data,
                session_id=session_id
            )
            
            # Update session records
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
        """Handle audio input message"""
        try:
            audio_msg = AudioInputMessage(**message_data)
            
            # Get audio data
            audio_data = audio_msg.get_audio_data()
            if not audio_data:
                raise ValueError("No audio data provided")
            
            # Get interview session
            session = self.interview_sessions.get(session_id)
            if not session:
                raise ValueError("Interview session not found")
            
            # Prepare input data
            input_data = {
                "audio_content": audio_data,
                "audio_format": audio_msg.get_audio_format(),
                "context": audio_msg.get_context() or session.get_context(),
                "original_question": "",  # Can be obtained from session
                "interview_style": self.connection_info[session_id].interview_style
            }
            
            # Call AI coordinator for processing
            result = await ai_coordinator.process_unified_input(
                input_data=input_data,
                session_id=session_id
            )
            
            # Update session records
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
        """Clean up connection resources"""
        try:
            # Close WebSocket connection
            if session_id in self.active_connections:
                websocket = self.active_connections[session_id]
                try:
                    await websocket.close()
                except:
                    pass  # Connection may already be closed
                del self.active_connections[session_id]
            
            # Update connection info
            if session_id in self.connection_info:
                self.connection_info[session_id].is_active = False
                # Note: Don't delete connection_info, keep for statistics and debugging
            
            # Note: Don't delete interview_sessions, maintain session memory
            # This way session data is preserved even if connection drops
            
            # Update statistics
            self.stats.active_connections = len(self.active_connections)
            
            logger.info(f"Connection cleaned up: {session_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up connection {session_id}: {e}")
    
    async def _heartbeat_loop(self):
        """Heartbeat check loop"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                current_time = datetime.now()
                inactive_sessions = []
                
                for session_id, info in self.connection_info.items():
                    if info.is_active:
                        # Check if inactive for more than 5 minutes
                        inactive_duration = (current_time - info.last_activity).total_seconds()
                        if inactive_duration > 300:  # 5 minutes
                            inactive_sessions.append(session_id)
                
                # Clean up inactive connections
                for session_id in inactive_sessions:
                    logger.info(f"Cleaning up inactive connection: {session_id}")
                    await self._cleanup_connection(session_id)
                
                # Update uptime statistics
                self.stats.uptime_seconds = (current_time - self.start_time).total_seconds()
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    def get_connection_stats(self) -> ConnectionStats:
        """Get connection statistics"""
        current_time = datetime.now()
        self.stats.uptime_seconds = (current_time - self.start_time).total_seconds()
        self.stats.active_connections = len(self.active_connections)
        return self.stats
    
    def get_active_sessions(self) -> List[str]:
        """Get list of all active Session IDs"""
        return list(self.active_connections.keys())
    
    def get_session_info(self, session_id: str) -> Optional[ConnectionInfo]:
        """Get connection info for specified session"""
        return self.connection_info.get(session_id)
    
    def is_session_active(self, session_id: str) -> bool:
        """Check if session is active"""
        return session_id in self.active_connections

# Global connection manager instance
connection_manager = ConnectionManager()
