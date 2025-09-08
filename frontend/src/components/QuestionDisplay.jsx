import React from 'react'

const QuestionDisplay = ({ question }) => {
  if (!question) return null

  return (
    <div className="question-display">
      <div className="question-container">
        <h2>Interview Question</h2>
        <div className="question-text">
          <p>{question.question}</p>
        </div>
        <div className="question-type">
          <small>Type: {question.type}</small>
        </div>
      </div>
    </div>
  )
}

export default QuestionDisplay