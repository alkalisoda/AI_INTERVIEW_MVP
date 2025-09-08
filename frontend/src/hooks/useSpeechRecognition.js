import { useState, useEffect, useRef } from 'react'

export const useSpeechRecognition = () => {
  const [isSupported, setIsSupported] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState('')
  
  const recognitionRef = useRef(null)
  const timeoutRef = useRef(null)

  useEffect(() => {
    // Check if browser supports speech recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    
    if (SpeechRecognition) {
      setIsSupported(true)
      
      recognitionRef.current = new SpeechRecognition()
      const recognition = recognitionRef.current
      
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'
      
      recognition.onstart = () => {
        setIsListening(true)
        setError('')
      }
      
      recognition.onresult = (event) => {
        let finalTranscript = ''
        let interimTranscript = ''
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcriptPart = event.results[i][0].transcript
          if (event.results[i].isFinal) {
            finalTranscript += transcriptPart
          } else {
            interimTranscript += transcriptPart
          }
        }
        
        setTranscript(finalTranscript + interimTranscript)
        
        // Auto-stop after silence (optional)
        if (finalTranscript) {
          clearTimeout(timeoutRef.current)
          timeoutRef.current = setTimeout(() => {
            if (recognitionRef.current && isListening) {
              recognition.stop()
            }
          }, 3000) // Stop after 3 seconds of silence
        }
      }
      
      recognition.onerror = (event) => {
        setError(`Speech recognition error: ${event.error}`)
        setIsListening(false)
      }
      
      recognition.onend = () => {
        setIsListening(false)
        clearTimeout(timeoutRef.current)
      }
    }
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
      clearTimeout(timeoutRef.current)
    }
  }, [])

  const startListening = () => {
    if (recognitionRef.current && !isListening) {
      try {
        recognitionRef.current.start()
      } catch (error) {
        setError('Failed to start speech recognition')
      }
    }
  }

  const stopListening = () => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop()
    }
  }

  const resetTranscript = () => {
    setTranscript('')
    setError('')
  }

  return {
    isSupported,
    isListening,
    transcript,
    error,
    startListening,
    stopListening,
    resetTranscript
  }
}