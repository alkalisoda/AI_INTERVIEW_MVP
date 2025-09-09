import React, { useState, useEffect, useRef } from 'react'
import api from '../utils/apiHelpers'

const ChatInterface = ({ interviewData, setInterviewData, onReset, userRole }) => {
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState('')
  const [inputMode, setInputMode] = useState('text') // 'text' or 'voice'
  const [isRecording, setIsRecording] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [currentState, setCurrentState] = useState('loading') // 'loading', 'interviewing', 'completed', 'error'
  const [interviewCompleted, setInterviewCompleted] = useState(false)
  const messagesEndRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

  useEffect(() => {
    startInterview()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Cleanup function
  const cleanupResourcesRef = useRef(() => {
    try {
      // Stop any ongoing recordings
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stop()
        setIsRecording(false)
      }
      
      // Stop any media streams
      if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop())
      }
      
      // Clear audio chunks
      audioChunksRef.current = []
      
      console.log('Resources cleaned up on unmount')
    } catch (error) {
      console.error('Error cleaning up resources on unmount:', error)
    }
  })

  useEffect(() => {
    // Cleanup resources when component unmounts
    return () => {
      cleanupResourcesRef.current()
    }
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const startInterview = async () => {
    try {
      const response = await api.post('/interview/start', {
        session_id: interviewData.sessionId
      })
      
      const startData = response.data
      
      // Add welcome message and first question
      const welcomeMessage = {
        id: Date.now(),
        type: 'bot',
        content: 'Hello! Welcome to the AI interview. I will ask you several questions, please answer them honestly. Let\'s begin!',
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
      
      setCurrentState('interviewing')
    } catch (error) {
      console.error('Failed to start interview:', error)
      setCurrentState('error')
      setMessages([{
        id: Date.now(),
        type: 'system',
        content: 'Sorry, unable to start interview. Please check network connection and try again.',
        timestamp: new Date().toISOString()
      }])
    }
  }

  const handleTextSubmit = async () => {
    if (!inputText.trim()) return

    // Add user message
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
      // Here we can call backend API to process the answer
      await processAnswer(userMessage.content)
    } catch (error) {
      console.error('Error processing answer:', error)
      addSystemMessage('Error processing answer, please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const processAnswer = async (answerText) => {
    try {
      // Add processing message
      const processingMessage = {
        id: Date.now(),
        type: 'system',
        content: '🤖 AI is analyzing your answer...',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, processingMessage])

      // Call gateway's unified processing interface
      const response = await api.post(`/interview/${interviewData.sessionId}/process-unified`, {
        text: answerText,
        context: messages.slice(-5).map(msg => `${msg.type}: ${msg.content}`).join('\n'), // Pass recent 5 messages as context
        interview_style: interviewData.interviewStyle || 'formal'
      })

      const aiResponse = response.data

      // Remove processing message
      setMessages(prev => prev.filter(msg => msg.id !== processingMessage.id))

      // Add AI's reply
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

      // Check if interview is completed
      if (aiResponse.response_type === 'interview_completed' || aiResponse.interview_completed) {
        setInterviewCompleted(true)
        setCurrentState('completed')
        
        // Cleanup resources
        cleanupResources()
        
        // Generate interview report after a short delay
        setTimeout(async () => {
          try {
            await generateInterviewReport()
          } catch (error) {
            console.error('Failed to generate report:', error)
          }
        }, 2000)
      }

      // Update interview data
      setInterviewData(prev => ({
        ...prev,
        conversations: [...prev.conversations, {
          userInput: answerText,
          aiResponse: aiResponse.ai_response,
          timestamp: new Date().toISOString(),
          completed: aiResponse.response_type === 'interview_completed'
        }]
      }))

    } catch (error) {
      console.error('Error processing answer:', error)
      
      // Remove processing message
      setMessages(prev => prev.filter(msg => msg.type !== 'system' || !msg.content.includes('analyzing')))
      
      let errorMessage = 'Error processing answer, please try again.'
      if (error.response?.data?.detail) {
        errorMessage = `Processing failed: ${error.response.data.detail}`
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
      addSystemMessage('Unable to access microphone, please check permission settings.')
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
      content: '🎤 Processing voice input...',
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, processingMessage])

    try {
      // Create FormData to upload audio file
      const formData = new FormData()
      
      // Convert audioBlob to file
      const audioFile = new File([audioBlob], 'recording.wav', { type: 'audio/wav' })
      formData.append('file', audioFile)
      
      // Add context information
      formData.append('context', messages.slice(-5).map(msg => `${msg.type}: ${msg.content}`).join('\n'))
      formData.append('interview_style', interviewData.interviewStyle || 'formal')

      // Call gateway's unified audio processing interface
      const response = await api.post(`/interview/${interviewData.sessionId}/process-unified-audio`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      const aiResponse = response.data
      
      // Remove processing message
      setMessages(prev => prev.filter(msg => msg.id !== processingMessage.id))
      
      // Add user message（显示识别的文字）
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

      // Add AI's reply
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

      // Check if interview is completed
      if (aiResponse.response_type === 'interview_completed' || aiResponse.interview_completed) {
        setInterviewCompleted(true)
        setCurrentState('completed')
        
        // Cleanup resources
        cleanupResources()
        
        // Generate interview report after a short delay
        setTimeout(async () => {
          try {
            await generateInterviewReport()
          } catch (error) {
            console.error('Failed to generate report:', error)
          }
        }, 2000)
      }

      // Update interview data
      setInterviewData(prev => ({
        ...prev,
        conversations: [...prev.conversations, {
          userInput: aiResponse.user_input,
          aiResponse: aiResponse.ai_response,
          timestamp: new Date().toISOString(),
          inputType: 'audio',
          transcriptionInfo: aiResponse.transcription_info,
          completed: aiResponse.response_type === 'interview_completed'
        }]
      }))
      
    } catch (error) {
      console.error('Error processing audio:', error)
      
      // Remove processing message
      setMessages(prev => prev.filter(msg => msg.id !== processingMessage.id))
      
      // Add error message
      let errorMessage = 'Voice processing failed, please try again or use text input.'
      if (error.response?.data?.detail) {
        errorMessage = `Processing failed: ${error.response.data.detail}`
      }
      addSystemMessage(`❌ ${errorMessage}`)
    } finally {
      setIsLoading(false)
    }
  }

  const cleanupResources = () => {
    try {
      // Stop any ongoing recordings
      if (isRecording && mediaRecorderRef.current) {
        mediaRecorderRef.current.stop()
        setIsRecording(false)
      }
      
      // Stop any media streams
      if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop())
      }
      
      // Clear audio chunks
      audioChunksRef.current = []
      
      // Clear input text
      setInputText('')
      setIsLoading(false)
      
      console.log('Resources cleaned up successfully')
    } catch (error) {
      console.error('Error cleaning up resources:', error)
    }
  }

  const generateInterviewReport = async () => {
    try {
      addSystemMessage('🎯 Generating interview report...')
      
      const candidateName = interviewData.candidateName || 'Anonymous'
      const response = await api.post(`/interview/${interviewData.sessionId}/generate-report`, {
        candidate_name: candidateName
      })
      
      const reportData = response.data
      if (reportData.success) {
        addSystemMessage(`✅ Interview report generated successfully for ${candidateName}!`)
        console.log('Report generated:', reportData)
      } else {
        addSystemMessage('⚠️ Report generation completed with some issues.')
      }
      
    } catch (error) {
      console.error('Failed to generate report:', error)
      addSystemMessage('❌ Failed to generate interview report.')
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
          <p className="text-gray-600">Preparing interview environment...</p>
        </div>
      </div>
    )
  }

  if (currentState === 'error') {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="text-red-500 text-4xl mb-4">⚠️</div>
          <p className="text-gray-600 mb-4">Interview startup failed</p>
          <button 
            onClick={onReset}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Restart
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
            <h2 className="font-semibold text-gray-800">AI Interviewer</h2>
            <p className="text-sm text-gray-500">
              {interviewCompleted ? (
                <span className="text-green-600">✅ Interview Completed</span>
              ) : (
                'Online • Interviewing'
              )}
            </p>
          </div>
        </div>
        <button 
          onClick={onReset}
          className="text-gray-500 hover:text-gray-700 px-3 py-1 rounded"
        >
          End Interview
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
                    <span className="text-xs opacity-75">Voice to Text</span>
                    {message.confidence && (
                      <span className="text-xs opacity-75">
                        • Confidence: {Math.round(message.confidence * 100)}%
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

      {/* Input Area or Completion Actions */}
      <div className="bg-white border-t border-gray-200 p-4">
        {interviewCompleted ? (
          /* Interview Completed - Show Return Button */
          <div className="flex flex-col items-center space-y-4">
            <div className="text-center">
              <div className="text-4xl mb-2">🎉</div>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">Interview Completed!</h3>
              <p className="text-sm text-gray-600">Thank you for participating in the AI interview.</p>
            </div>
            <button
              onClick={onReset}
              className="px-8 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors font-medium flex items-center space-x-2"
            >
              <span>🏠</span>
              <span>Return to Home</span>
            </button>
          </div>
        ) : (
          /* Normal Interview - Show Input */
          <>
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
                      placeholder="Enter your answer..."
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      disabled={isLoading}
                    />
                    <button
                      onClick={handleTextSubmit}
                      disabled={!inputText.trim() || isLoading}
                      className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      Send
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
                      {isRecording ? '🔴 Click to Stop Recording' : '🎤 Click to Start Recording'}
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Status Info */}
            <div className="mt-2 text-xs text-gray-500 text-center">
              {inputMode === 'text' ? 'Press Enter to send, Shift + Enter for new line' : 'Voice input supported, automatically converts to text'}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default ChatInterface
