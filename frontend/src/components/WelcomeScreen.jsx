import React, { useState } from 'react'

const WelcomeScreen = ({ onStart }) => {
  const [candidateName, setCandidateName] = useState('')
  const [interviewStyle, setInterviewStyle] = useState('formal')
  const [nameError, setNameError] = useState('')

  const handleNameChange = (e) => {
    const name = e.target.value
    setCandidateName(name)
    if (nameError && name.trim()) {
      setNameError('')
    }
  }

  const handleStyleChange = (style) => {
    setInterviewStyle(style)
  }

  const handleStart = () => {
    const trimmedName = candidateName.trim()
    if (!trimmedName) {
      setNameError('Please enter your name to continue')
      return
    }
    
    if (trimmedName.length < 2) {
      setNameError('Name must be at least 2 characters long')
      return
    }

    // Pass candidate name and interview style to parent component
    onStart({
      candidateName: trimmedName,
      interviewStyle: interviewStyle
    })
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleStart()
    }
  }

  return (
    <div className="welcome-screen">
      <div className="welcome-container">
        {/* Header Section */}
        <div className="bubble-section header-bubble">
          <h1>🤖 AI Interview System</h1>
          <div className="greeting-message">
            <p>
              Hello, I am your AI interviewer. I will ask you a few common interview questions. 
              You can answer using your <strong>voice</strong> or <strong>text input</strong> - whatever feels more comfortable for you.
            </p>
          </div>
        </div>
        
        {/* Personal Information Bubble */}
        <div className="bubble-section info-bubble personal-info-bubble">
          <div className="bubble-header">
            <span className="bubble-icon">📝</span>
            <h3>Personal Information</h3>
          </div>
          <div className="name-input-group">
            <label htmlFor="candidateName" className="name-label">
              Your Name <span className="required">*</span>
            </label>
            <input
              id="candidateName"
              type="text"
              value={candidateName}
              onChange={handleNameChange}
              onKeyPress={handleKeyPress}
              placeholder="Enter your full name"
              className={`name-input ${nameError ? 'error' : ''}`}
              maxLength={50}
            />
            {nameError && (
              <div className="error-message">
                {nameError}
              </div>
            )}
          </div>
        </div>
        
        {/* Interview Information Bubble */}
        <div className="bubble-section info-bubble expectation-bubble">
          <div className="bubble-header">
            <span className="bubble-icon">📋</span>
            <h3>What to expect</h3>
          </div>
          <ul className="expectation-list">
            <li>1 self-introduction + 3 behavioral questions</li>
            <li>Voice or text input options available</li>
            <li>AI-generated follow-up questions</li>
            <li>Approximately 5-10 minutes total</li>
          </ul>
        </div>

        {/* Interview Style Bubble */}
        <div className="bubble-section style-bubble">
          <div className="bubble-header">
            <span className="bubble-icon">🎯</span>
            <h3>Choose interview style</h3>
          </div>
          <div className="style-buttons-grid">
            <button 
              className={`style-card ${interviewStyle === 'formal' ? 'active' : ''}`}
              onClick={() => handleStyleChange('formal')}
            >
              <div className="style-icon">👔</div>
              <div className="style-title">Formal</div>
              <div className="style-desc">Professional & structured</div>
            </button>
            <button 
              className={`style-card ${interviewStyle === 'casual' ? 'active' : ''}`}
              onClick={() => handleStyleChange('casual')}
            >
              <div className="style-icon">😊</div>
              <div className="style-title">Casual</div>
              <div className="style-desc">Relaxed & friendly</div>
            </button>
            <button 
              className={`style-card ${interviewStyle === 'campus' ? 'active' : ''}`}
              onClick={() => handleStyleChange('campus')}
            >
              <div className="style-icon">🎓</div>
              <div className="style-title">Campus</div>
              <div className="style-desc">Student-oriented</div>
            </button>
          </div>
        </div>

        {/* Start Button Section */}
        <div className="bubble-section start-bubble">
          <button 
            className="start-button"
            onClick={handleStart}
            disabled={!candidateName.trim()}
          >
            <span className="start-icon">🚀</span>
            Start Interview
          </button>
        </div>

        {/* Technical Requirements Bubble */}
        <div className="bubble-section tech-bubble">
          <div className="tech-requirements">
            <div className="tech-tip">
              <span className="tip-icon">💡</span>
              <div className="tip-content">
                <strong>Voice input:</strong> Use Chrome or Safari for best voice recognition. Make sure your microphone is enabled.
              </div>
            </div>
            <div className="tech-tip">
              <span className="tip-icon">⌨️</span>
              <div className="tip-content">
                <strong>Text input:</strong> Available as an alternative option during the interview.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default WelcomeScreen