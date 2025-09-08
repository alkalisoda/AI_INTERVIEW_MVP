import React, { useState, useEffect } from 'react'
import QuestionDisplay from './QuestionDisplay'
import VoiceRecorder from './VoiceRecorder'
import TranscriptionDisplay from './TranscriptionDisplay'
import FollowUpQuestion from './FollowUpQuestion'
import { generateFollowUp } from '../utils/apiHelpers'
import api from '../utils/apiHelpers'

const InterviewFlow = ({ interviewData, setInterviewData, onReset, userRole }) => {
  const [currentState, setCurrentState] = useState('loading') // loading, question, recording, transcribing, followup, completed
  const [currentTranscript, setCurrentTranscript] = useState('')
  const [currentFollowUp, setCurrentFollowUp] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    startInterview()
  }, [])

  const startInterview = async () => {
    try {
      // Use backend's /interview/start endpoint to begin interview
      const response = await api.post('/interview/start', {
        session_id: interviewData.sessionId
      })
      
      const startData = response.data
      
      // Create questions array, starting from the returned first question
      const questions = [{
        id: 1,
        question: startData.first_question.question,
        type: startData.first_question.type,
        category: startData.first_question.category
      }]
      
      setInterviewData(prev => ({
        ...prev,
        questions: questions,
        totalQuestions: startData.total_questions,
        currentQuestionIndex: 0
      }))
      
      setCurrentState('question')
    } catch (error) {
      console.error('Failed to start interview:', error)
      setCurrentState('error')
    }
  }

  const handleAnswerSubmit = async (transcript) => {
    setCurrentTranscript(transcript)
    setCurrentState('transcribing')
    setIsLoading(true)

    try {
      // Generate follow-up question
      const followUp = await generateFollowUp(
        interviewData.questions[interviewData.currentQuestionIndex].id,
        transcript,
        interviewData.conversations
      )
      
      setCurrentFollowUp(followUp.follow_up_question)
      
      // Update conversation history
      const newConversation = {
        question: interviewData.questions[interviewData.currentQuestionIndex].question,
        answer: transcript,
        followUp: followUp.follow_up_question
      }
      
      setInterviewData(prev => ({
        ...prev,
        conversations: [...prev.conversations, newConversation]
      }))
      
      setCurrentState('followup')
    } catch (error) {
      console.error('Failed to generate follow-up:', error)
      // Skip follow-up and move to next question
      moveToNextQuestion()
    } finally {
      setIsLoading(false)
    }
  }

  const handleFollowUpAnswer = (transcript) => {
    // Update the last conversation with follow-up answer
    setInterviewData(prev => {
      const updatedConversations = [...prev.conversations]
      updatedConversations[updatedConversations.length - 1].followUpAnswer = transcript
      return {
        ...prev,
        conversations: updatedConversations
      }
    })
    
    moveToNextQuestion()
  }

  const moveToNextQuestion = () => {
    if (interviewData.currentQuestionIndex < (interviewData.totalQuestions || 1) - 1) {
      setInterviewData(prev => ({
        ...prev,
        currentQuestionIndex: prev.currentQuestionIndex + 1
      }))
      setCurrentState('question')
      setCurrentTranscript('')
      setCurrentFollowUp('')
      // TODO: Need to get next question from backend
    } else {
      setCurrentState('completed')
    }
  }

  const getCurrentQuestion = () => {
    return interviewData.questions[interviewData.currentQuestionIndex]
  }

  if (currentState === 'loading') {
    return (
      <div className="loading text-center py-8">
        <div className="text-lg text-gray-600 mb-4">
          {userRole === 'interviewee' ? 'Preparing interview questions...' : 'Preparing interview assistance tools...'}
        </div>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
      </div>
    )
  }

  if (currentState === 'error') {
    return (
      <div className="error">
        <p>Failed to load interview questions. Please try again.</p>
        <button onClick={onReset}>Restart</button>
      </div>
    )
  }

  if (currentState === 'completed') {
    return (
      <div className="interview-completed text-center py-8">
        <div className="text-4xl mb-4">🎉</div>
        <h2 className="text-2xl font-bold text-gray-800 mb-4">
          {userRole === 'interviewee' ? 'Interview Complete!' : 'Interview Assistance Complete!'}
        </h2>
        <p className="text-gray-600 mb-6">
          {userRole === 'interviewee' 
            ? 'Thank you for completing the AI interview, good luck!' 
            : 'Interview assistance tool has provided you with complete support.'}
        </p>
        <div className="bg-gray-50 rounded-lg p-4 mb-6 max-w-md mx-auto">
          <h3 className="font-semibold text-gray-700 mb-2">Interview Summary:</h3>
          <p className="text-sm text-gray-600">Questions answered: {interviewData.conversations.length}</p>
          <p className="text-sm text-gray-600">Estimated time: ~5 minutes</p>
        </div>
        <button 
          onClick={onReset}
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          Start New Interview
        </button>
      </div>
    )
  }

  return (
    <div className="interview-flow">
      <div className="progress-bar">
        <div 
          className="progress" 
          style={{ 
            width: `${((interviewData.currentQuestionIndex + 1) / (interviewData.totalQuestions || 1)) * 100}%` 
          }}
        ></div>
      </div>

      <div className="question-counter">
        Question {interviewData.currentQuestionIndex + 1} of {interviewData.totalQuestions || 1}
      </div>

      {currentState === 'question' && (
        <>
          <QuestionDisplay question={getCurrentQuestion()} />
          <VoiceRecorder 
            onTranscriptReady={handleAnswerSubmit}
            onStateChange={setCurrentState}
          />
        </>
      )}

      {currentState === 'recording' && (
        <div className="recording-state">
          <p>🎤 Recording... Speak your answer clearly</p>
          <VoiceRecorder 
            onTranscriptReady={handleAnswerSubmit}
            onStateChange={setCurrentState}
            autoStart={true}
          />
        </div>
      )}

      {currentState === 'transcribing' && (
        <TranscriptionDisplay 
          transcript={currentTranscript}
          isLoading={isLoading}
        />
      )}

      {currentState === 'followup' && (
        <FollowUpQuestion 
          question={currentFollowUp}
          onAnswer={handleFollowUpAnswer}
          onSkip={moveToNextQuestion}
        />
      )}
    </div>
  )
}

export default InterviewFlow