# AI Interview MVP

A comprehensive AI-powered behavioral interview simulator with real-time voice interaction and intelligent follow-up questions. Experience a 5-minute interactive interview session with AI-driven conversation flow and contextual questioning.

## ✨ Features

- **🎙️ Voice-Enabled Interviews**: Real-time speech recognition using OpenAI Whisper API with Web Speech API fallback
- **🧠 Intelligent Follow-ups**: AI-generated contextual follow-up questions based on candidate responses using GPT-4
- **📱 Multi-Modal Support**: Seamless voice and text input with automatic browser compatibility detection
- **⚡ Real-time Processing**: Live transcription and instant AI response generation
- **🎯 Behavioral Focus**: 3 structured behavioral questions with STAR method evaluation
- **💾 Session Management**: Persistent conversation memory and interview state tracking
- **📱 Mobile-Responsive**: Optimized for both desktop and mobile devices with touch-friendly interface

## 🏗️ System Architecture

### Backend (FastAPI + Python)
- **API Gateway** (`api_gateway/`): RESTful endpoints with unified processing
- **AI Coordinator** (`coordinator.py`): Orchestrates speech recognition, planning, and chatbot modules
- **Speech Recognition** (`speech_recognition/`): OpenAI Whisper integration for audio transcription
- **Interview Planner** (`planner/`): LangChain-powered response analysis and decision making
- **Chatbot Module** (`chatbot/`): Context-aware follow-up generation with multiple strategies
- **Core Utilities** (`core/`): Shared configuration and response formatting

### Frontend (React + Vite)
- **Interview Flow** (`InterviewFlow.jsx`): State machine managing interview progression
- **Voice Interface** (`VoiceRecorder.jsx` + `useSpeechRecognition.js`): Web Speech API with fallback strategies
- **Real-time UI**: Live transcription display and conversational interface
- **Responsive Design**: Mobile-first approach with modern CSS
- **Error Handling**: Graceful degradation with user-friendly messaging

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern Python web framework for APIs
- **LangChain**: AI application framework for complex reasoning
- **OpenAI APIs**: GPT-4 for conversation, Whisper for speech recognition
- **Pydantic**: Data validation and settings management
- **Uvicorn**: ASGI server for production deployment

### Frontend
- **React 18**: Modern UI library with hooks
- **Vite**: Fast build tool and development server
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client for API communication
- **Web Speech API**: Browser-native speech recognition

## 📋 Prerequisites

- **Python 3.11+** (with conda recommended)
- **Node.js 16+** and npm
- **OpenAI API Key** (for GPT-4 and Whisper APIs)
- **Windows**: Use CMD (Command Prompt) instead of PowerShell due to execution policy restrictions
  - Open CMD by pressing `Win + R`, type `cmd`, and press Enter
  - Or search for "Command Prompt" in the Start menu

## 🚀 Quick Start

### Option 1: One-Click Start (Windows)
```cmd
git clone https://github.com/alkalisoda/AI_INTERVIEW_MVP.git
cd AI_INTERVIEW_MVP\ai-interview-project
```

### Option 2: Manual Setup

#### 1. Environment Setup
```cmd
git clone https://github.com/alkalisoda/AI_INTERVIEW_MVP.git
cd AI_INTERVIEW_MVP\ai-interview-project

REM Create conda environment
conda create -n ai-interview python=3.11
conda activate ai-interview
```

#### 2. Backend Setup
```cmd
cd backend
pip install -r requirements.txt
```

Create `.env` file in backend folder:
```env
OPENAI_API_KEY=your_openai_api_key_here
ENVIRONMENT=development
DEBUG=true
```

Start backend:
```cmd
REM Make sure conda environment is activated
conda activate ai-interview
cd backend
python main.py
```
🌐 Backend: `http://localhost:8000` | 📚 API Docs: `http://localhost:8000/docs`

#### 3. Frontend Setup (New Terminal)
```cmd
cd frontend
npm install
```

**Note**: Frontend is configured with Vite proxy, so no additional `.env` file is needed for local development.

Start frontend:
```cmd
npm run dev
```
🌐 Frontend: `http://localhost:3000`

## 📡 Key API Endpoints

### 🎯 Interview Flow
- `GET /api/v1/interview/questions` - Get behavioral interview questions
- `POST /api/v1/interview/{session_id}/process-unified` - Process text responses with AI
- `POST /api/v1/interview/{session_id}/process-unified-audio` - Process audio with transcription + AI

### 🔧 System Health
- `GET /health` - Comprehensive health check with AI service status
- `GET /` - System information and status

### 🎛️ Interactive API Documentation
Visit `http://localhost:8000/docs` for complete Swagger/OpenAPI documentation with live testing interface.

## 📁 Project Structure

```
ai-interview-project/
├── backend/                    # FastAPI backend
│   ├── main.py                # Application entry point
│   ├── ai_backend/            # AI processing modules
│   │   ├── coordinator.py     # Orchestrates AI modules
│   │   ├── config.py          # LangChain configuration
│   │   ├── models.py          # Data models
│   │   ├── speech_recognition/# OpenAI Whisper integration
│   │   │   └── recognizer.py
│   │   ├── planner/           # Response analysis & decision making
│   │   │   └── interview_planner.py
│   │   └── chatbot/           # Follow-up question generation
│   │       └── interviewer_bot.py
│   ├── api_gateway/           # API layer & request handling
│   │   ├── routes.py          # REST endpoints
│   │   ├── models.py          # Request/response models
│   │   └── websocket_manager.py # WebSocket support
│   ├── core/                  # Shared utilities
│   │   ├── config.py          # Application settings
│   │   └── utils.py           # Response formatting
│   ├── tests/                 # Test suite
│   └── requirements.txt       # Python dependencies
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── App.jsx           # Main application component
│   │   ├── components/       # React UI components
│   │   │   ├── InterviewFlow.jsx      # Interview state machine
│   │   │   ├── WelcomeScreen.jsx      # Introduction screen
│   │   │   ├── ChatInterface.jsx      # Chat-like interface
│   │   │   └── [other components]
│   │   ├── hooks/            # Custom React hooks
│   │   │   └── useSpeechRecognition.js
│   │   ├── utils/            # API helpers & utilities
│   │   │   └── apiHelpers.js
│   │   └── styles/           # CSS styling
│   ├── package.json
│   └── vite.config.js        # Vite configuration
├── start_all.bat             # Windows batch file to start both services
├── start_backend.bat         # Backend startup script
├── README.md                 # Project documentation
└── CLAUDE.md                # Development guidelines
```

## 🌐 Browser Compatibility

### Voice Recognition Support
- ✅ **Chrome 25+** - Full voice support
- ✅ **Safari 14.1+** - Full voice support  
- ⚠️ **Firefox/Edge** - Text input fallback
- 📱 **Mobile** - Responsive design with voice support on compatible browsers

## 🧪 Testing

### Backend Testing
```cmd
cd backend
conda activate ai-interview
pytest
```

### Frontend Testing
```cmd
cd frontend
npm run lint        # ESLint code quality checks
```
*Note: Comprehensive automated test suite planned for future versions*

## 🚀 Deployment

### Production Backend
```cmd
conda activate ai-interview
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

### Production Frontend
```cmd
npm run build
REM Deploy dist/ folder to your hosting service (Vercel, Netlify, etc.)
```

### Environment Variables for Production
Ensure all production `.env` files have appropriate values for your hosting environment.

## 🔧 Configuration

### Environment Variables

#### Backend
- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `ENVIRONMENT` - development/production
- `DEBUG` - Enable debug mode (true/false)
- `SERVER_HOST` - Server host (default: localhost)
- `SERVER_PORT` - Server port (default: 8000)
- `MAX_AUDIO_SIZE` - Maximum audio file size in MB
- `SUPPORTED_AUDIO_FORMATS` - Comma-separated audio formats

#### Frontend
- Frontend uses Vite proxy configuration for API calls in development
- For production builds, configure `VITE_API_URL` if needed

## 🔮 Roadmap & Future Enhancements

### Short-term Goals
- [ ] Comprehensive automated test suite (Jest/React Testing Library + pytest)
- [ ] Interview analytics and performance metrics
- [ ] Enhanced mobile voice recognition support

### Medium-term Goals
- [ ] Custom behavioral question templates
- [ ] Multi-language interview support
- [ ] Advanced AI coaching and feedback features
- [ ] Interview session replay and analysis

### Long-term Vision
- [ ] Video interview capabilities with computer vision
- [ ] Integration with popular HR platforms (Workday, BambooHR)
- [ ] Candidate assessment scoring algorithms
- [ ] Multi-interviewer panel simulation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 🆘 Troubleshooting

### Common Issues

**🔧 Backend won't start**
- Ensure conda environment is activated: `conda activate ai-interview`
- Make sure you're in the `backend` directory when running `python main.py`
- Verify OpenAI API key is set in `.env` file
- Check port 8000 isn't already in use
- Install dependencies: `pip install -r requirements.txt`

**🎙️ Voice recording not working**
- Use Chrome or Safari for full voice support
- Check browser permissions for microphone access
- Firefox/Edge users: System automatically falls back to text input

**⚡ API calls timing out**
- Verify OpenAI API key has sufficient credits
- Check internet connection for API requests
- Review logs at `http://localhost:8000/health` for AI service status

**🔧 Frontend won't start**
- Ensure Node.js 16+ is installed: `node --version`
- Install dependencies: `npm install` in frontend directory
- Check port 3000 isn't already in use
- Clear npm cache if needed: `npm cache clean --force`

**🐍 Conda environment issues**
- Ensure conda is installed and in PATH
- Create environment with specific Python version: `conda create -n ai-interview python=3.11 -y`
- If activation fails, try: `conda init` then restart terminal
- List environments to verify: `conda env list`

### Getting Help
1. 📚 Check [API documentation](http://localhost:8000/docs) when running locally
2. 📖 Review troubleshooting in `CLAUDE.md`
3. 🐛 Open an issue on GitHub with error details and logs

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **OpenAI** for GPT-4 and Whisper APIs powering the AI capabilities
- **LangChain** for the flexible AI application framework  
- **FastAPI** for the high-performance Python backend framework
- **React** and **Vite** for the modern, responsive frontend experience

**Built with ❤️ for realistic interview practice and AI-powered conversation**