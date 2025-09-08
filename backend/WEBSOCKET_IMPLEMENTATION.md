# AI Interview WebSocket Implementation

## 概述

本文档描述了AI Interview系统的WebSocket实现，提供了前端与后端之间的长连接通信能力，支持实时的文本和音频输入处理。

## 架构设计

### 核心组件

1. **WebSocket连接管理器** (`websocket_manager.py`)
   - 管理所有WebSocket连接的生命周期
   - 处理消息路由和数据解码
   - 维护连接状态和统计信息
   - 实现心跳检查和连接清理

2. **WebSocket消息模型** (`models.py`)
   - 定义了完整的WebSocket消息协议
   - 支持文本输入、音频输入、状态消息等
   - 提供数据验证和序列化功能

3. **WebSocket路由** (`routes.py`)
   - 提供WebSocket端点和管理API
   - 集成现有的HTTP API，共享会话存储
   - 确保对话记忆的持久化

## 功能特性

### 1. 长连接支持
- 支持持久的WebSocket连接
- 自动心跳检查，防止连接超时
- 连接断开后自动清理资源

### 2. 数据解码
- **文本输入**: 直接处理JSON格式的文本数据
- **音频输入**: 支持Base64编码的音频数据
- **格式支持**: wav, mp3, m4a, webm等多种音频格式

### 3. 智能路由
- 自动判断输入类型（文本/音频）
- 路由到相应的AI后端模块（语音识别、规划器、聊天机器人）
- 统一的响应格式

### 4. 会话持久化
- 会话数据在连接断开后仍然保留
- HTTP API和WebSocket API共享会话存储
- 确保对话记忆在整个服务生命周期中保持

### 5. 错误处理
- 完善的错误捕获和处理机制
- 优雅的错误消息返回
- 连接异常时的自动清理

## WebSocket消息协议

### 消息格式

所有WebSocket消息都遵循以下基本格式：

```json
{
  "type": "message_type",
  "session_id": "session_identifier",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "data": {
    // 消息特定数据
  }
}
```

### 客户端到服务器消息

#### 1. 连接消息
```json
{
  "type": "connect",
  "session_id": "optional_session_id",
  "data": {
    "interview_style": "formal",
    "client_info": {}
  }
}
```

#### 2. 文本输入消息
```json
{
  "type": "text_input",
  "session_id": "session_id",
  "data": {
    "text": "用户输入的文本",
    "context": "可选的上下文信息"
  }
}
```

#### 3. 音频输入消息
```json
{
  "type": "audio_input",
  "session_id": "session_id",
  "data": {
    "audio_data": "base64_encoded_audio_data",
    "audio_format": "wav",
    "context": "可选的上下文信息"
  }
}
```

#### 4. 心跳消息
```json
{
  "type": "ping",
  "session_id": "session_id",
  "data": {}
}
```

#### 5. 断开连接消息
```json
{
  "type": "disconnect",
  "session_id": "session_id",
  "data": {}
}
```

### 服务器到客户端消息

#### 1. 连接确认消息
```json
{
  "type": "connected",
  "session_id": "assigned_session_id",
  "data": {
    "status": "connected",
    "server_info": {"version": "2.0.0"}
  }
}
```

#### 2. AI响应消息
```json
{
  "type": "ai_response",
  "session_id": "session_id",
  "data": {
    "user_input": "用户输入的文本",
    "ai_response": "AI生成的回复",
    "response_type": "question",
    "strategy_used": "deep_dive",
    "focus_area": "technical_skills",
    "confidence": 0.85,
    "processing_time": 2.34,
    "transcription_info": {
      "confidence": 0.92,
      "duration": 3.5,
      "language": "en"
    }
  }
}
```

#### 3. 转录消息
```json
{
  "type": "transcription",
  "session_id": "session_id",
  "data": {
    "transcription": "转录的文本",
    "confidence": 0.92,
    "processing_time": 1.23
  }
}
```

#### 4. 错误消息
```json
{
  "type": "error",
  "session_id": "session_id",
  "data": {
    "error": "error_type",
    "message": "错误描述",
    "details": "详细错误信息"
  }
}
```

#### 5. 心跳响应消息
```json
{
  "type": "pong",
  "session_id": "session_id",
  "data": {
    "timestamp": "2024-01-01T12:00:00.000Z"
  }
}
```

#### 6. 状态消息
```json
{
  "type": "status",
  "session_id": "session_id",
  "data": {
    "status": "processing",
    "message": "正在处理您的输入..."
  }
}
```

## API端点

### WebSocket端点

#### 主要WebSocket端点
- `ws://localhost:8000/api/v1/ws/{session_id}` - 指定会话ID的WebSocket连接
- `ws://localhost:8000/api/v1/ws` - 自动生成会话ID的WebSocket连接

### 管理API端点

#### 获取WebSocket统计信息
```http
GET /api/v1/websocket/stats
```

响应示例：
```json
{
  "success": true,
  "data": {
    "websocket_stats": {
      "total_connections": 10,
      "active_connections": 3,
      "messages_sent": 156,
      "messages_received": 142,
      "errors_count": 2,
      "uptime_seconds": 3600.5
    },
    "active_sessions": ["session_1", "session_2", "session_3"]
  }
}
```

#### 获取活跃会话列表
```http
GET /api/v1/websocket/sessions
```

#### 获取特定会话信息
```http
GET /api/v1/websocket/sessions/{session_id}
```

#### 向特定会话发送消息
```http
POST /api/v1/websocket/sessions/{session_id}/message
```

#### 广播消息到所有会话
```http
POST /api/v1/websocket/broadcast
```

## 使用示例

### 前端JavaScript示例

```javascript
// 建立WebSocket连接
const ws = new WebSocket('ws://localhost:8000/api/v1/ws');

// 连接建立后发送连接消息
ws.onopen = function() {
    const connectMsg = {
        type: 'connect',
        session_id: 'optional_session_id',
        timestamp: new Date().toISOString(),
        data: {
            interview_style: 'formal',
            client_info: {}
        }
    };
    ws.send(JSON.stringify(connectMsg));
};

// 处理接收到的消息
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case 'connected':
            console.log('连接成功，会话ID:', message.session_id);
            break;
        case 'ai_response':
            console.log('AI回复:', message.data.ai_response);
            break;
        case 'error':
            console.error('错误:', message.data.message);
            break;
    }
};

// 发送文本输入
function sendTextInput(text) {
    const message = {
        type: 'text_input',
        session_id: currentSessionId,
        timestamp: new Date().toISOString(),
        data: {
            text: text,
            context: ''
        }
    };
    ws.send(JSON.stringify(message));
}

// 发送音频输入
function sendAudioInput(audioBlob) {
    const reader = new FileReader();
    reader.onload = function() {
        const base64Data = reader.result.split(',')[1];
        const message = {
            type: 'audio_input',
            session_id: currentSessionId,
            timestamp: new Date().toISOString(),
            data: {
                audio_data: base64Data,
                audio_format: 'wav',
                context: ''
            }
        };
        ws.send(JSON.stringify(message));
    };
    reader.readAsDataURL(audioBlob);
}
```

### Python客户端示例

```python
import asyncio
import websockets
import json
import base64

async def websocket_client():
    uri = "ws://localhost:8000/api/v1/ws"
    
    async with websockets.connect(uri) as websocket:
        # 等待连接确认
        response = await websocket.recv()
        message = json.loads(response)
        session_id = message.get('session_id')
        
        # 发送文本输入
        text_message = {
            "type": "text_input",
            "session_id": session_id,
            "timestamp": "2024-01-01T12:00:00.000Z",
            "data": {
                "text": "Hello, I'm ready for the interview.",
                "context": ""
            }
        }
        
        await websocket.send(json.dumps(text_message))
        
        # 接收响应
        response = await websocket.recv()
        ai_response = json.loads(response)
        print("AI回复:", ai_response['data']['ai_response'])

# 运行客户端
asyncio.run(websocket_client())
```

## 部署和配置

### 依赖安装

确保安装了WebSocket相关依赖：

```bash
pip install websockets
```

### 环境配置

在`.env`文件中配置相关参数：

```env
# WebSocket配置
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_CONNECTION_TIMEOUT=300
MAX_WEBSOCKET_CONNECTIONS=100
```

### 启动服务

```bash
# 激活conda环境
conda activate ai-interview

# 启动后端服务
python main.py
```

## 测试

### 运行WebSocket测试

```bash
# Windows
test_websocket.bat

# 或直接运行Python测试
python test_websocket_client.py
```

### 测试场景

测试客户端包含以下测试场景：

1. **文本对话测试**: 测试纯文本输入和AI回复
2. **音频对话测试**: 测试音频文件上传、转录和AI回复
3. **混合对话测试**: 测试文本和音频输入的混合使用
4. **心跳测试**: 测试连接保活机制

## 性能优化

### 连接管理优化

1. **连接池管理**: 限制最大并发连接数
2. **内存优化**: 及时清理断开的连接
3. **心跳机制**: 自动检测和清理僵尸连接

### 消息处理优化

1. **异步处理**: 所有I/O操作使用async/await
2. **并发处理**: 支持多个会话并发处理
3. **错误恢复**: 单个会话错误不影响其他会话

### 数据传输优化

1. **压缩**: 对大型音频数据进行压缩
2. **分片**: 大文件分片传输
3. **缓存**: 缓存频繁使用的数据

## 故障排除

### 常见问题

1. **连接失败**
   - 检查服务器是否启动
   - 确认端口号正确
   - 检查防火墙设置

2. **音频处理失败**
   - 确认音频格式支持
   - 检查文件大小限制
   - 验证Base64编码正确性

3. **会话丢失**
   - 检查会话ID是否正确
   - 确认服务器未重启
   - 验证会话存储配置

### 调试工具

1. **日志查看**: 查看服务器日志了解详细错误信息
2. **WebSocket工具**: 使用浏览器开发者工具或专用WebSocket客户端
3. **API测试**: 使用管理API端点检查连接状态

## 安全考虑

### 认证和授权

1. **连接验证**: 可在连接建立时验证客户端身份
2. **会话隔离**: 确保不同会话之间的数据隔离
3. **权限控制**: 限制管理API的访问权限

### 数据保护

1. **传输加密**: 在生产环境中使用WSS（WebSocket Secure）
2. **数据清理**: 及时清理敏感的音频和文本数据
3. **日志脱敏**: 避免在日志中记录敏感信息

## 扩展性

### 水平扩展

1. **负载均衡**: 使用WebSocket兼容的负载均衡器
2. **会话粘性**: 确保同一会话的请求路由到同一服务器
3. **状态共享**: 使用Redis等外部存储共享会话状态

### 功能扩展

1. **多媒体支持**: 扩展支持视频输入
2. **实时协作**: 支持多人同时参与面试
3. **推送通知**: 实现服务器主动推送功能

## 总结

本WebSocket实现提供了完整的长连接通信解决方案，支持：

- ✅ 长连接维持和管理
- ✅ 文本和音频数据的实时处理
- ✅ 智能路由到AI后端服务
- ✅ 会话记忆持久化
- ✅ 完善的错误处理机制
- ✅ 丰富的管理和监控API
- ✅ 高性能的并发处理
- ✅ 全面的测试覆盖

该实现确保了前端可以通过WebSocket与后端建立稳定的长连接，实现实时的面试交互，同时保证了对话记忆在整个服务生命周期中的持续性。
