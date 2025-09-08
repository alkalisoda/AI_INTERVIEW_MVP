import React, { useState, useEffect, useRef } from 'react'
import api from '../utils/apiHelpers'

const ChatInterface = ({ interviewData, setInterviewData, onReset, userRole }) => {
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState('')
  const [inputMode, setInputMode] = useState('text') // 'text' or 'voice'
  const [isRecording, setIsRecording] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [currentState, setCurrentState] = useState('loading')
  const messagesEndRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

  useEffect(() => {
    startInterview()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const startInterview = async () => {
    try {
      const response = await api.post('/interview/start', {
        session_id: interviewData.sessionId
      })
      
      const startData = response.data
      
      // 添加欢迎消息和第一个问题
      const welcomeMessage = {
        id: Date.now(),
        type: 'bot',
        content: '您好！欢迎参加AI面试。我将为您提出几个问题，请您如实回答。让我们开始吧！',
        timestamp: new Date().toISOString()
      }

      const firstQuestion = {
        id: Date.now() + 1,
        type: 'bot',
        content: startData.first_question.question,
        timestamp: new Date().toISOString(),
        questionId: startData.first_question.id
      }

      setMessages([welcomeMessage, firstQuestion])
      
      setInterviewData(prev => ({
        ...prev,
        totalQuestions: startData.total_questions,
        currentQuestionIndex: 0,
        currentQuestionId: startData.first_question.id
      }))
      
      setCurrentState('question')
    } catch (error) {
      console.error('Failed to start interview:', error)
      setCurrentState('error')
      setMessages([{
        id: Date.now(),
        type: 'system',
        content: '抱歉，无法开始面试。请检查网络连接后重试。',
        timestamp: new Date().toISOString()
      }])
    }
  }

  const handleTextSubmit = async () => {
    if (!inputText.trim()) return

    // 添加用户消息
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputText.trim(),
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInputText('')
    setIsLoading(true)

    try {
      // 这里可以调用后端API处理回答
      await processAnswer(userMessage.content)
    } catch (error) {
      console.error('Error processing answer:', error)
      addSystemMessage('处理回答时出现错误，请重试。')
    } finally {
      setIsLoading(false)
    }
  }

  const processAnswer = async (answerText) => {
    try {
      // 添加处理中的消息
      const processingMessage = {
        id: Date.now(),
        type: 'system',
        content: '🤖 AI正在分析您的回答...',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, processingMessage])

      // 调用gateway的统一处理接口
      const response = await api.post(`/interview/${interviewData.sessionId}/process-unified`, {
        text: answerText,
        context: messages.slice(-5).map(msg => `${msg.type}: ${msg.content}`).join('\n'), // 传递最近5条消息作为上下文
        interview_style: 'formal'
      })

      const aiResponse = response.data

      // 移除处理中的消息
      setMessages(prev => prev.filter(msg => msg.id !== processingMessage.id))

      // 添加AI的回复
      const aiMessage = {
        id: Date.now(),
        type: 'bot',
        content: aiResponse.ai_response,
        timestamp: new Date().toISOString(),
        responseType: aiResponse.response_type,
        strategyUsed: aiResponse.strategy_used,
        confidence: aiResponse.confidence,
        processingTime: aiResponse.processing_time
      }

      setMessages(prev => [...prev, aiMessage])

      // 更新面试数据
      setInterviewData(prev => ({
        ...prev,
        conversations: [...prev.conversations, {
          userInput: answerText,
          aiResponse: aiResponse.ai_response,
          timestamp: new Date().toISOString()
        }]
      }))

    } catch (error) {
      console.error('Error processing answer:', error)
      
      // 移除处理中的消息
      setMessages(prev => prev.filter(msg => msg.type !== 'system' || !msg.content.includes('分析')))
      
      let errorMessage = '处理回答时出现错误，请重试。'
      if (error.response?.data?.detail) {
        errorMessage = `处理失败: ${error.response.data.detail}`
      }
      addSystemMessage(`❌ ${errorMessage}`)
    }
  }

  const addSystemMessage = (content) => {
    const systemMessage = {
      id: Date.now(),
      type: 'system',
      content,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, systemMessage])
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleTextSubmit()
    }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorderRef.current = new MediaRecorder(stream)
      audioChunksRef.current = []

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data)
      }

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' })
        await processAudio(audioBlob)
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorderRef.current.start()
      setIsRecording(true)
    } catch (error) {
      console.error('Error starting recording:', error)
      addSystemMessage('无法访问麦克风，请检查权限设置。')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const processAudio = async (audioBlob) => {
    setIsLoading(true)
    
    // 添加处理中的消息
    const processingMessage = {
      id: Date.now(),
      type: 'system',
      content: '🎤 正在处理语音输入...',
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, processingMessage])

    try {
      // 创建FormData来上传音频文件
      const formData = new FormData()
      
      // 将audioBlob转换为文件
      const audioFile = new File([audioBlob], 'recording.wav', { type: 'audio/wav' })
      formData.append('file', audioFile)
      
      // 添加上下文信息
      formData.append('context', messages.slice(-5).map(msg => `${msg.type}: ${msg.content}`).join('\n'))
      formData.append('interview_style', 'formal')

      // 调用gateway的统一音频处理接口
      const response = await api.post(`/interview/${interviewData.sessionId}/process-unified-audio`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      const aiResponse = response.data
      
      // 移除处理中的消息
      setMessages(prev => prev.filter(msg => msg.id !== processingMessage.id))
      
      // 添加用户消息（显示识别的文字）
      const userMessage = {
        id: Date.now(),
        type: 'user',
        content: aiResponse.user_input,
        timestamp: new Date().toISOString(),
        isVoice: true,
        confidence: aiResponse.transcription_info?.confidence,
        processingTime: aiResponse.transcription_info?.transcription_time
      }
      setMessages(prev => [...prev, userMessage])

      // 添加AI的回复
      const aiMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: aiResponse.ai_response,
        timestamp: new Date().toISOString(),
        responseType: aiResponse.response_type,
        strategyUsed: aiResponse.strategy_used,
        confidence: aiResponse.confidence,
        processingTime: aiResponse.processing_time
      }
      setMessages(prev => [...prev, aiMessage])

      // 更新面试数据
      setInterviewData(prev => ({
        ...prev,
        conversations: [...prev.conversations, {
          userInput: aiResponse.user_input,
          aiResponse: aiResponse.ai_response,
          timestamp: new Date().toISOString(),
          inputType: 'audio',
          transcriptionInfo: aiResponse.transcription_info
        }]
      }))
      
    } catch (error) {
      console.error('Error processing audio:', error)
      
      // 移除处理中的消息
      setMessages(prev => prev.filter(msg => msg.id !== processingMessage.id))
      
      // 添加错误消息
      let errorMessage = '语音处理失败，请重试或使用文字输入。'
      if (error.response?.data?.detail) {
        errorMessage = `处理失败: ${error.response.data.detail}`
      }
      addSystemMessage(`❌ ${errorMessage}`)
    } finally {
      setIsLoading(false)
    }
  }

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  if (currentState === 'loading') {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">正在准备面试环境...</p>
        </div>
      </div>
    )
  }

  if (currentState === 'error') {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="text-red-500 text-4xl mb-4">⚠️</div>
          <p className="text-gray-600 mb-4">面试启动失败</p>
          <button 
            onClick={onReset}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            重新开始
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4 flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
            <span className="text-white text-lg">🤖</span>
          </div>
          <div>
            <h2 className="font-semibold text-gray-800">AI面试官</h2>
            <p className="text-sm text-gray-500">在线 • 正在面试中</p>
          </div>
        </div>
        <button 
          onClick={onReset}
          className="text-gray-500 hover:text-gray-700 px-3 py-1 rounded"
        >
          结束面试
        </button>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`flex max-w-xs lg:max-w-md ${message.type === 'user' ? 'flex-row-reverse' : 'flex-row'} items-end space-x-2`}>
              {/* Avatar */}
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                message.type === 'user' 
                  ? 'bg-green-500 text-white ml-2' 
                  : message.type === 'bot'
                  ? 'bg-blue-500 text-white mr-2'
                  : 'bg-gray-500 text-white mr-2'
              }`}>
                {message.type === 'user' ? '👤' : message.type === 'bot' ? '🤖' : 'ℹ️'}
              </div>

              {/* Message Bubble */}
              <div className={`px-4 py-2 rounded-lg ${
                message.type === 'user'
                  ? 'bg-green-500 text-white rounded-br-sm'
                  : message.type === 'bot'
                  ? 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm'
                  : 'bg-yellow-100 text-yellow-800 border border-yellow-200'
              }`}>
                <p className="text-sm">{message.content}</p>
                {message.isVoice && (
                  <div className="mt-1 flex items-center space-x-1">
                    <span className="text-xs opacity-75">🎤</span>
                    <span className="text-xs opacity-75">语音转文字</span>
                    {message.confidence && (
                      <span className="text-xs opacity-75">
                        • 置信度: {Math.round(message.confidence * 100)}%
                      </span>
                    )}
                    {message.processingTime && (
                      <span className="text-xs opacity-75">
                        • {message.processingTime.toFixed(1)}s
                      </span>
                    )}
                  </div>
                )}
                <div className={`text-xs mt-1 ${
                  message.type === 'user' ? 'text-green-100' : 'text-gray-500'
                }`}>
                  {formatTime(message.timestamp)}
                </div>
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-end space-x-2">
              <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white mr-2">
                🤖
              </div>
              <div className="bg-white border border-gray-200 px-4 py-2 rounded-lg rounded-bl-sm">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 p-4">
        <div className="flex items-center space-x-3">
          {/* Input Mode Toggle */}
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setInputMode('text')}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                inputMode === 'text'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              📝
            </button>
            <button
              onClick={() => setInputMode('voice')}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                inputMode === 'voice'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              🎤
            </button>
          </div>

          {/* Input Field */}
          <div className="flex-1 flex items-center space-x-2">
            {inputMode === 'text' ? (
              <>
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="输入您的回答..."
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={isLoading}
                />
                <button
                  onClick={handleTextSubmit}
                  disabled={!inputText.trim() || isLoading}
                  className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  发送
                </button>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <button
                  onClick={isRecording ? stopRecording : startRecording}
                  disabled={isLoading}
                  className={`px-8 py-3 rounded-lg font-medium transition-all ${
                    isRecording
                      ? 'bg-red-500 text-white hover:bg-red-600 animate-pulse'
                      : 'bg-blue-500 text-white hover:bg-blue-600'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {isRecording ? '🔴 点击停止录音' : '🎤 点击开始录音'}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Status Info */}
        <div className="mt-2 text-xs text-gray-500 text-center">
          {inputMode === 'text' ? '按 Enter 发送，Shift + Enter 换行' : '支持语音输入，自动转换为文字'}
        </div>
      </div>
    </div>
  )
}

export default ChatInterface
