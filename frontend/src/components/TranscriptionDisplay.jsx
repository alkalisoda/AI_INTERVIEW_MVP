import React from 'react'

const TranscriptionDisplay = ({ transcript, isLoading }) => {
  return (
    <div className="transcription-display">
      <div className="transcription-container">
        <h3>Your Answer:</h3>
        <div className="transcript-text">
          <p>{transcript}</p>
        </div>
        
        {isLoading && (
          <div className="loading-followup">
            <div className="spinner"></div>
            <p>Generating follow-up question...</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default TranscriptionDisplay