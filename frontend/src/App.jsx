import React, { useState } from 'react'
import ChatInterface from './components/ChatInterface'
import { initializeInterviewSession } from './utils/apiHelpers'

function App() {
  const [currentView, setCurrentView] = useState('roleSelection') // roleSelection, connecting, interview
  const [userRole, setUserRole] = useState(null) // 'interviewer' or 'interviewee'
  const [connectionError, setConnectionError] = useState(null)
  const [interviewData, setInterviewData] = useState({
    questions: [],
    currentQuestionIndex: 0,
    conversations: [],
    sessionId: null,
    totalQuestions: 0
  })

  const handleRoleSelection = async (role) => {
    setUserRole(role)
    setCurrentView('connecting')
    setConnectionError(null)

    try {
      // 立即与后端建立连接
      const sessionData = await initializeInterviewSession(role)
      
      setInterviewData(prev => ({
        ...prev,
        sessionId: sessionData.session_id || Date.now().toString()
      }))
      
      setCurrentView('interview')
    } catch (error) {
      console.error('Failed to connect to backend:', error)
      setConnectionError('无法连接到后端服务，请检查网络连接或稍后重试。')
      setCurrentView('roleSelection')
    }
  }

  const handleReset = () => {
    setCurrentView('roleSelection')
    setUserRole(null)
    setConnectionError(null)
    setInterviewData({
      questions: [],
      currentQuestionIndex: 0,
      conversations: [],
      sessionId: null,
      totalQuestions: 0
    })
  }

  if (currentView === 'roleSelection') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="max-w-2xl mx-auto p-8 bg-white rounded-2xl shadow-xl">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-800 mb-4">
              🤖 AI Interview System
            </h1>
            <p className="text-xl text-gray-600 mb-8">
              欢迎使用 AI 面试系统！
            </p>
            
            <div className="space-y-6">
              <h2 className="text-2xl font-semibold text-gray-700 mb-6">
                准备开始面试
              </h2>
              
              {connectionError && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center">
                    <div className="text-red-500 mr-3">⚠️</div>
                    <div>
                      <p className="text-red-800 font-medium">连接失败</p>
                      <p className="text-red-600 text-sm">{connectionError}</p>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="max-w-md mx-auto">
                <button 
                  onClick={() => handleRoleSelection('interviewee')}
                  className="w-full p-8 bg-blue-50 rounded-xl border-2 border-blue-200 hover:border-blue-400 hover:bg-blue-100 transition-all duration-200 group"
                >
                  <div className="text-5xl mb-4 group-hover:scale-110 transition-transform">👤</div>
                  <h3 className="text-2xl font-semibold text-blue-800 mb-3">开始面试</h3>
                  <p className="text-blue-600 mb-2">我是来参加面试的候选人</p>
                  <p className="text-sm text-blue-500">点击开始与AI面试官对话</p>
                </button>
                
                {/* 保留面试官接口供未来扩展使用 - 目前隐藏 */}
                {false && (
                  <button 
                    onClick={() => handleRoleSelection('interviewer')}
                    className="w-full p-6 bg-green-50 rounded-xl border-2 border-green-200 hover:border-green-400 hover:bg-green-100 transition-all duration-200 group mt-4"
                  >
                    <div className="text-4xl mb-4 group-hover:scale-110 transition-transform">👔</div>
                    <h3 className="text-xl font-semibold text-green-800 mb-2">面试官模式</h3>
                    <p className="text-green-600">使用AI辅助进行面试</p>
                  </button>
                )}
              </div>
              
              <div className="mt-8 text-sm text-gray-500">
                <p>💡 选择角色后将进入相应的面试界面</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (currentView === 'connecting') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="max-w-md mx-auto p-8 bg-white rounded-2xl shadow-xl text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-6"></div>
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">正在连接后端服务</h2>
          <p className="text-gray-600 mb-6">正在初始化面试环境，请稍候...</p>
          <div className="text-sm text-gray-500">
            <p>⚡ 建立AI连接</p>
            <p>🎯 准备面试问题</p>
            <p>🎤 初始化语音识别</p>
          </div>
        </div>
      </div>
    )
  }

  if (currentView === 'interview') {
    return (
      <div className="h-screen bg-gray-100 flex flex-col">
        <ChatInterface 
          interviewData={interviewData}
          setInterviewData={setInterviewData}
          onReset={handleReset}
          userRole={userRole}
        />
      </div>
    )
  }

  return null
}

export default App