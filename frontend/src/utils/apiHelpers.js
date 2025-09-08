import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const fetchQuestions = async () => {
  try {
    const response = await api.get('/questions')
    return response.data
  } catch (error) {
    throw new Error(`Failed to fetch questions: ${error.message}`)
  }
}

export const generateFollowUp = async (questionId, answer, conversationHistory = []) => {
  try {
    const response = await api.post('/generate-followup', {
      question_id: questionId,
      answer: answer,
      conversation_history: conversationHistory
    })
    return response.data
  } catch (error) {
    throw new Error(`Failed to generate follow-up: ${error.message}`)
  }
}

export const transcribeAudio = async (audioFile, sessionId) => {
  try {
    const formData = new FormData()
    formData.append('file', audioFile)
    
    const response = await api.post(`/interview/${sessionId}/transcribe`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    
    return response.data
  } catch (error) {
    throw new Error(`Failed to transcribe audio: ${error.message}`)
  }
}

export const healthCheck = async () => {
  try {
    const response = await api.get('/health')
    return response.data
  } catch (error) {
    throw new Error(`Health check failed: ${error.message}`)
  }
}

// Initialize interview session with backend
export const initializeInterviewSession = async (userRole = 'interviewee') => {
  try {
    const response = await api.post('/interview/initialize', {
      role: userRole,
      timestamp: new Date().toISOString()
    })
    return response.data
  } catch (error) {
    throw new Error(`Failed to initialize interview session: ${error.message}`)
  }
}

export default api