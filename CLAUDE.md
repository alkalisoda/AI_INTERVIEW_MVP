# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a 5-minute behavioral interview simulator with voice interaction and AI-generated follow-up questions. The application consists of a React frontend and Python FastAPI backend that integrates with OpenAI's GPT and Whisper APIs.

## Development Commands

### Backend (Python FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
python main.py  # Runs on http://localhost:8000
```

### Frontend (React + Vite)
```bash
cd frontend  
npm install
npm run dev      # Development server on http://localhost:3000
npm run build    # Production build
npm run lint     # ESLint checking
npm run preview  # Preview production build
```

### Testing
```bash
# Backend
cd backend && pytest

# Frontend (manual testing checklist in README.md)
# No automated tests implemented yet
```

## Architecture Overview

### Request Flow
1. **WelcomeScreen** → **InterviewFlow** → **QuestionDisplay** + **VoiceRecorder**
2. Voice input → **useSpeechRecognition** hook → transcription
3. **TranscriptionDisplay** → API call to generate follow-up → **FollowUpQuestion**
4. Cycle repeats for 3 behavioral questions → Interview completion

### Backend Architecture
- **main.py**: FastAPI app with CORS middleware and startup configuration
- **api_gateway/**: Frontend-backend communication layer
  - **routes.py**: API endpoints (`/questions`, `/generate-followup`, `/transcribe`, `/health`) 
  - **models.py**: Request/response data models
- **ai_backend/**: Core AI processing modules
  - **coordinator.py**: Orchestrates all AI modules
  - **speech_recognition/recognizer.py**: OpenAI Whisper API integration
  - **planner/interview_planner.py**: LangChain-powered response analysis and planning
  - **chatbot/interviewer_bot.py**: LangChain-powered follow-up question generation
  - **config.py**: LangChain configuration and utilities
- **core/**: Shared utilities and configuration

### Frontend Architecture
- **App.jsx**: Main state management (welcome/interview screens)
- **InterviewFlow.jsx**: Core interview state machine (loading → question → recording → transcribing → followup → completed)
- **useSpeechRecognition.js**: Web Speech API wrapper with error handling
- **apiHelpers.js**: Axios-based API client with error interceptors

## Key Integration Points

### Voice Recognition Fallback Strategy
The app implements a graceful degradation pattern:
1. Check Web Speech API support (`window.SpeechRecognition || window.webkitSpeechRecognition`)
2. If unsupported, automatically switch to text input mode
3. Chrome/Safari: Full voice support | Firefox/Edge: Text-only fallback

### LangChain Integration
- **Planner Module**: Uses structured output parsing and chain processing for response analysis
- **Chatbot Module**: Multiple generation strategies (deep_dive, behavioral, reflection, situational)
- **Follow-up Generation**: LangChain chains with prompt templates and callback monitoring
- **Audio Transcription**: Handles file upload → temporary storage → Whisper API → cleanup
- **Error Handling**: Graceful fallback to template-based questions on LangChain failures

## Environment Configuration

Both frontend and backend require environment files:
- Copy `.env.example` to `.env` in respective directories
- Backend requires `OPENAI_API_KEY`
- Frontend connects to backend via `VITE_API_URL` (defaults to `http://localhost:8000/api`)

## Browser Compatibility Notes

- **Voice Recognition**: Chrome 25+, Safari 14.1+ (full support) | Firefox, Edge (text fallback only)
- **Critical**: Always test voice functionality in supported browsers
- **Mobile**: Responsive design prioritizes mobile-first approach

## Common Development Patterns

### Adding New Questions
Modify the questions array in `backend/api_gateway/routes.py:get_interview_questions()`

### Customizing AI Prompts  
Edit prompt templates in `backend/ai_backend/config.py` or chain definitions in planner/chatbot modules

### LangChain Chain Modifications
- **Planner chains**: `backend/ai_backend/planner/interview_planner.py`
- **Chatbot chains**: `backend/ai_backend/chatbot/interviewer_bot.py`

### API Error Handling
All API calls in `frontend/src/utils/apiHelpers.js` include error interceptors and throw descriptive errors

## Performance Considerations

- **API Response Time**: 2-3 seconds for follow-up generation (LangChain + OpenAI GPT)
- **Voice Recognition**: Real-time transcription with 3-second silence timeout
- **State Management**: Single interview state object passed between components
- **LangChain Processing**: Structured output parsing with error fixing and callback monitoring
- **Mobile Loading**: Vite bundling optimized for mobile networks