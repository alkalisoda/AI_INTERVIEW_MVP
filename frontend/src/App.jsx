import React, { useState } from 'react'
import ChatInterface from './components/ChatInterface'
import WelcomeScreen from './components/WelcomeScreen'
import { initializeInterviewSession } from './utils/apiHelpers'

function App() {
  const [currentView, setCurrentView] = useState('roleSelection') // roleSelection, nameInput, connecting, interview
  const [userRole, setUserRole] = useState(null) // 'interviewer' or 'interviewee'
  const [connectionError, setConnectionError] = useState(null)
  const [interviewData, setInterviewData] = useState({
    questions: [],
    currentQuestionIndex: 0,
    conversations: [],
    sessionId: null,
    totalQuestions: 0,
    candidateName: '',
    interviewStyle: 'formal'
  })

  const handleRoleSelection = async (role, interviewInfo = null) => {
    setUserRole(role)
    setCurrentView('connecting')
    setConnectionError(null)

    try {
      // Immediately establish connection with backend
      const sessionData = await initializeInterviewSession(role)
      
      setInterviewData(prev => ({
        ...prev,
        sessionId: sessionData.session_id || Date.now().toString(),
        candidateName: interviewInfo?.candidateName || '',
        interviewStyle: interviewInfo?.interviewStyle || 'formal'
      }))
      
      setCurrentView('interview')
    } catch (error) {
      console.error('Failed to connect to backend:', error)
      setConnectionError('Unable to connect to backend service, please check network connection or try again later.')
      setCurrentView('roleSelection')
    }
  }

  const handleNameSubmit = async (interviewInfo) => {
    await handleRoleSelection('interviewee', interviewInfo)
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
      totalQuestions: 0,
      candidateName: '',
      interviewStyle: 'formal'
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
              Welcome to the AI Interview System!
            </p>
            
            <div className="space-y-6">
              <h2 className="text-2xl font-semibold text-gray-700 mb-6">
                Ready to Start Interview
              </h2>
              
              {connectionError && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center">
                    <div className="text-red-500 mr-3">⚠️</div>
                    <div>
                      <p className="text-red-800 font-medium">Connection Failed</p>
                      <p className="text-red-600 text-sm">{connectionError}</p>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="max-w-md mx-auto">
                <button 
                  onClick={() => setCurrentView('nameInput')}
                  className="w-full p-8 bg-blue-50 rounded-xl border-2 border-blue-200 hover:border-blue-400 hover:bg-blue-100 transition-all duration-200 group"
                >
                  <div className="text-5xl mb-4 group-hover:scale-110 transition-transform">👤</div>
                  <h3 className="text-2xl font-semibold text-blue-800 mb-3">Start Interview</h3>
                  <p className="text-blue-600 mb-2">I am a candidate here for the interview</p>
                  <p className="text-sm text-blue-500">Click to start conversation with AI interviewer</p>
                </button>
                
                {/* Keep interviewer interface for future expansion - currently hidden */}
                {false && (
                  <button 
                    onClick={() => handleRoleSelection('interviewer')}
                    className="w-full p-6 bg-green-50 rounded-xl border-2 border-green-200 hover:border-green-400 hover:bg-green-100 transition-all duration-200 group mt-4"
                  >
                    <div className="text-4xl mb-4 group-hover:scale-110 transition-transform">👔</div>
                    <h3 className="text-xl font-semibold text-green-800 mb-2">Interviewer Mode</h3>
                    <p className="text-green-600">Use AI assistance for conducting interviews</p>
                  </button>
                )}
              </div>
              
              <div className="mt-8 text-sm text-gray-500">
                <p>💡 After selecting a role, you will enter the corresponding interview interface</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (currentView === 'nameInput') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="max-w-2xl mx-auto p-8 bg-white rounded-2xl shadow-xl">
          <WelcomeScreen onStart={handleNameSubmit} />
          <div className="mt-6 text-center">
            <button 
              onClick={() => setCurrentView('roleSelection')}
              className="text-gray-500 hover:text-gray-700 underline"
            >
              ← Back to role selection
            </button>
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
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">Connecting to Backend Service</h2>
          <p className="text-gray-600 mb-6">Initializing interview environment, please wait...</p>
          <div className="text-sm text-gray-500">
            <p>⚡ Establishing AI connection</p>
            <p>🎯 Preparing interview questions</p>
            <p>🎤 Initializing voice recognition</p>
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