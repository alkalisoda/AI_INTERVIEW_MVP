import React, { useState } from 'react'

const FollowUpQuestion = ({ question, onAnswer, onSkip }) => {
  const [answer, setAnswer] = useState('')
  const [isTextMode, setIsTextMode] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (answer.trim()) {
      onAnswer(answer.trim())
      setAnswer('')
    }
  }

  return (
    <div className="followup-question">
      <div className="followup-container">
        <h3>Follow-up Question:</h3>
        <div className="question-text">
          <p>{question}</p>
        </div>

        {!isTextMode ? (
          <div className="voice-answer">
            <button 
              onClick={() => setIsTextMode(true)}
              className="voice-btn"
            >
              🎤 Record Answer
            </button>
            <p className="or-text">or</p>
            <button 
              onClick={() => setIsTextMode(true)}
              className="text-btn"
            >
              ✏️ Type Answer
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="text-answer">
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Type your answer to the follow-up question..."
              rows="3"
              className="answer-input"
            />
            <div className="answer-actions">
              <button 
                type="submit" 
                className="submit-btn"
                disabled={!answer.trim()}
              >
                Submit Answer
              </button>
              <button 
                type="button"
                onClick={() => setIsTextMode(false)}
                className="back-btn"
              >
                Back
              </button>
            </div>
          </form>
        )}

        <div className="skip-option">
          <button 
            onClick={onSkip}
            className="skip-btn"
          >
            Skip Follow-up →
          </button>
        </div>
      </div>
    </div>
  )
}

export default FollowUpQuestion