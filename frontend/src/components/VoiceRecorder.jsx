import React, { useState, useEffect, useRef } from 'react'
import { useSpeechRecognition } from '../hooks/useSpeechRecognition'

const VoiceRecorder = ({ onTranscriptReady, onStateChange, autoStart = false }) => {
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [textInput, setTextInput] = useState('')
  const [useTextMode, setUseTextMode] = useState(false)
  const timerRef = useRef(null)

  const {
    isSupported,
    transcript,
    isListening,
    startListening,
    stopListening,
    resetTranscript
  } = useSpeechRecognition()

  useEffect(() => {
    if (autoStart && isSupported) {
      handleStartRecording()
    }
  }, [autoStart, isSupported])

  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1)
      }, 1000)
    } else {
      clearInterval(timerRef.current)
    }

    return () => clearInterval(timerRef.current)
  }, [isRecording])

  const handleStartRecording = async () => {
    if (!isSupported) {
      setUseTextMode(true)
      return
    }

    try {
      resetTranscript()
      await startListening()
      setIsRecording(true)
      setRecordingTime(0)
      onStateChange('recording')
    } catch (error) {
      console.error('Failed to start recording:', error)
      setUseTextMode(true)
    }
  }

  const handleStopRecording = () => {
    stopListening()
    setIsRecording(false)
    clearInterval(timerRef.current)
    
    if (transcript.trim()) {
      onTranscriptReady(transcript)
    }
  }

  const handleTextSubmit = (e) => {
    e.preventDefault()
    if (textInput.trim()) {
      onTranscriptReady(textInput.trim())
      setTextInput('')
    }
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  if (useTextMode || !isSupported) {
    return (
      <div className="voice-recorder text-mode">
        <div className="text-input-container">
          <h3>Voice not supported - Please type your answer:</h3>
          <form onSubmit={handleTextSubmit}>
            <textarea
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Type your answer here..."
              rows="4"
              className="text-input"
            />
            <button 
              type="submit" 
              className="submit-btn"
              disabled={!textInput.trim()}
            >
              Submit Answer
            </button>
          </form>
          {isSupported && (
            <button 
              onClick={() => setUseTextMode(false)}
              className="switch-mode-btn"
            >
              Try Voice Input Instead
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="voice-recorder">
      <div className="recording-controls">
        {!isRecording ? (
          <button 
            onClick={handleStartRecording}
            className="record-btn"
          >
            🎤 Start Recording
          </button>
        ) : (
          <div className="recording-active">
            <button 
              onClick={handleStopRecording}
              className="stop-btn"
            >
              ⏹️ Stop Recording
            </button>
            <div className="recording-info">
              <div className="recording-indicator">🔴 Recording</div>
              <div className="timer">{formatTime(recordingTime)}</div>
            </div>
          </div>
        )}
      </div>

      {transcript && (
        <div className="live-transcript">
          <h4>Your answer:</h4>
          <p>{transcript}</p>
        </div>
      )}

      <div className="fallback-options">
        <button 
          onClick={() => setUseTextMode(true)}
          className="text-fallback-btn"
        >
          Type Instead
        </button>
      </div>
    </div>
  )
}

export default VoiceRecorder