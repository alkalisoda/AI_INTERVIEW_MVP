# AI Interviewer Web App MVP

A 5-minute behavioral interview simulator with voice interaction and AI-generated follow-up questions.

## 🎯 Project Overview

This project implements an AI-powered interview simulator that:
- Presents 3 behavioral interview questions
- Records user responses via voice (with text fallback)
- Generates contextual follow-up questions using OpenAI GPT
- Provides a mobile-friendly, professional interview experience

**Demo Timeline**: Built in 3 days (Sep 7-9, 2025)

## 🏗️ Architecture

### Frontend (React + Vite)
- **Voice Recognition**: Web Speech API with fallback to text input
- **UI Framework**: Modern React with functional components and hooks
- **Styling**: Custom CSS with mobile-first responsive design
- **API Integration**: Axios for backend communication

### Backend (Python FastAPI)
- **API Framework**: FastAPI with async support
- **LLM Integration**: OpenAI GPT-3.5-turbo for follow-up questions
- **Speech Processing**: OpenAI Whisper API for audio transcription
- **CORS**: Configured for frontend-backend communication

## 📁 Project Structure

```
ai-interview-project/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── WelcomeScreen.jsx
│   │   │   ├── InterviewFlow.jsx
│   │   │   ├── QuestionDisplay.jsx
│   │   │   ├── VoiceRecorder.jsx
│   │   │   ├── TranscriptionDisplay.jsx
│   │   │   └── FollowUpQuestion.jsx
│   │   ├── hooks/
│   │   │   └── useSpeechRecognition.js
│   │   ├── utils/
│   │   │   └── apiHelpers.js
│   │   ├── styles/
│   │   │   ├── index.css
│   │   │   └── App.css
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── interview_routes.py
│   │   └── services/
│   │       ├── openai_service.py
│   │       └── speech_service.py
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Node.js (v16+)
- Python (v3.8+)
- OpenAI API Key

### Backend Setup
1. Navigate to backend directory:
   ```bash
   cd ai-interview-project/backend
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env file and add your OpenAI API key
   ```

5. Start backend server:
   ```bash
   python main.py
   ```
   Server will run on `http://localhost:8000`

### Frontend Setup
1. Navigate to frontend directory:
   ```bash
   cd ai-interview-project/frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Verify API URL points to backend (should be correct by default)
   ```

4. Start development server:
   ```bash
   npm run dev
   ```
   Frontend will run on `http://localhost:3000`

## 🎤 Features

### Core Features
- ✅ Welcome screen with clear instructions
- ✅ 3 behavioral interview questions
- ✅ Voice recording with real-time transcription
- ✅ Text input fallback for compatibility
- ✅ AI-generated follow-up questions
- ✅ Mobile-friendly responsive design

### Bonus Features
- ✅ Customizable interview style (formal/casual/campus)
- ✅ Interview progress tracking
- ✅ Professional UI/UX with smooth transitions
- ✅ Error handling and fallback options

## 🔧 API Endpoints

### Backend Routes (`/api`)
- `GET /questions` - Get interview questions
- `POST /generate-followup` - Generate follow-up questions
- `POST /transcribe` - Transcribe audio files
- `GET /health` - Health check

## 🌐 Browser Compatibility

### Voice Recognition Support
- ✅ **Chrome 25+**: Full support
- ✅ **Safari 14.1+**: Full support
- ❌ **Firefox**: Not supported (text fallback available)
- ❌ **Edge**: Limited support (text fallback available)

### Fallback Strategy
When voice recognition is unavailable, the app automatically provides:
1. Text input fields for all responses
2. Same interview flow and AI follow-ups
3. Full functionality without voice features

## 🚀 Deployment

### Frontend (Vercel/Netlify)
1. Build the frontend:
   ```bash
   npm run build
   ```

2. Deploy to your preferred platform:
   - **Vercel**: Connect GitHub repo, auto-deploy
   - **Netlify**: Drag & drop `dist/` folder

### Backend (Railway/Heroku/DigitalOcean)
1. Ensure all dependencies are in `requirements.txt`
2. Configure environment variables on hosting platform
3. Deploy using platform-specific instructions

## 🧪 Testing

### Manual Testing Checklist
- [ ] Welcome screen loads correctly
- [ ] All 3 questions display properly
- [ ] Voice recording works in supported browsers
- [ ] Text fallback functions when voice fails
- [ ] Follow-up questions generate correctly
- [ ] Mobile responsive design works
- [ ] Interview completion flow works

### Running Tests
```bash
# Backend tests
cd backend
pytest

# Frontend tests (if implemented)
cd frontend
npm test
```

## 🔑 Environment Variables

### Backend (.env)
```
OPENAI_API_KEY=your_openai_api_key_here
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
ALLOWED_ORIGINS=http://localhost:3000
ENVIRONMENT=development
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000/api
VITE_NODE_ENV=development
```

## 🛠️ Development

### Adding New Questions
Edit `backend/app/api/interview_routes.py`:
```python
questions = [
    {
        "id": 4,
        "question": "Your new question here",
        "type": "behavioral"
    }
]
```

### Customizing AI Prompts
Modify `backend/app/services/openai_service.py` to adjust follow-up generation logic.

### Styling Changes
Update `frontend/src/styles/App.css` for UI modifications.

## 📈 Performance Considerations

- **API Response Time**: ~2-3 seconds for follow-up generation
- **Voice Recognition**: Real-time transcription
- **Bundle Size**: Optimized for mobile loading
- **Error Handling**: Graceful degradation for all failures

## 🐛 Known Issues & Limitations

1. **Voice Recognition**: Limited browser support
2. **Internet Dependency**: Requires connection for OpenAI API
3. **Audio Quality**: Performance depends on microphone quality
4. **Rate Limits**: OpenAI API has usage limits

## 📝 Future Enhancements

- [ ] Interview recording/playback
- [ ] Multiple language support
- [ ] Interview analytics/feedback
- [ ] Custom question sets
- [ ] User authentication
- [ ] Interview history

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is created for educational/demo purposes. Please ensure OpenAI API usage complies with their terms of service.

## 📞 Support

For issues or questions:
1. Check this README
2. Review the code comments
3. Test with the provided example environment files
4. Ensure all dependencies are installed correctly

---

**Built in 3 days as an AI Interview MVP Demo** 🚀