import React from 'react'

const WelcomeScreen = ({ onStart }) => {
  return (
    <div className="welcome-screen">
      <div className="welcome-container">
        <h1>AI Interviewer</h1>
        <div className="greeting-message">
          <p>
            Hello, I am your AI interviewer. I will ask you a few common interview questions. 
            Please answer using your voice.
          </p>
        </div>
        
        <div className="interview-info">
          <h3>What to expect:</h3>
          <ul>
            <li>3 behavioral interview questions</li>
            <li>Voice-based interaction with text fallback</li>
            <li>AI-generated follow-up questions</li>
            <li>Approximately 5 minutes total</li>
          </ul>
        </div>

        <div className="tone-selection">
          <h3>Choose interview style:</h3>
          <div className="tone-buttons">
            <button className="tone-btn" data-tone="formal">Formal</button>
            <button className="tone-btn" data-tone="casual">Casual</button>
            <button className="tone-btn" data-tone="campus">Campus</button>
          </div>
        </div>

        <button 
          className="start-button"
          onClick={onStart}
        >
          Start Interview
        </button>

        <div className="tech-requirements">
          <p>
            <small>
              💡 For best experience, use Chrome or Safari for voice recognition.
              Make sure your microphone is enabled.
            </small>
          </p>
        </div>
      </div>
    </div>
  )
}

export default WelcomeScreen