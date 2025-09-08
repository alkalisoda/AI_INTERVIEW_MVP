# AI Interview MVP

A comprehensive AI-powered interview system that simulates behavioral interviews with real-time voice interaction and intelligent follow-up questions.

## 🚀 Features

- **Voice-Enabled Interviews**: Real-time speech recognition using OpenAI Whisper API
- **Intelligent Follow-ups**: AI-generated contextual follow-up questions based on candidate responses
- **Multi-Modal Support**: Support for both voice and text input with graceful fallbacks
- **Real-time Processing**: Live transcription and instant AI response generation
- **Behavioral Interview Focus**: Specialized prompts for behavioral interview scenarios
- **Session Management**: Persistent conversation memory and interview state tracking
- **Mobile-Responsive**: Optimized for both desktop and mobile devices

## 🏗️ Architecture

### Backend (FastAPI + Python)
- **API Gateway**: RESTful endpoints and WebSocket support
- **AI Coordinator**: Orchestrates multiple AI modules
- **Speech Recognition**: OpenAI Whisper integration for audio transcription
- **Interview Planner**: LangChain-powered response analysis and decision making
- **Chatbot Module**: Context-aware follow-up question generation
- **Modular Design**: Clean separation of concerns with dependency injection

### Frontend (React + Vite)
- **Interactive UI**: Intuitive interview flow with real-time feedback
- **Voice Recording**: Web Speech API with fallback strategies
- **State Management**: Centralized interview state with React hooks
- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **Error Handling**: Graceful degradation and user-friendly error messages

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

- **Python 3.8+**
- **Node.js 16+** and npm
- **OpenAI API Key** (for GPT-4 and Whisper)

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/alkalisoda/AI_INTERVIEW_MVP.git
cd AI_INTERVIEW_MVP
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
ENVIRONMENT=development
DEBUG=true
```

Start backend:
```bash
python main.py
```
Backend runs on `http://localhost:8000`

### 3. Frontend Setup
```bash
cd frontend
npm install
```

Create `.env` file:
```env
VITE_API_URL=http://localhost:8000/api
```

Start frontend:
```bash
npm run dev
```
Frontend runs on `http://localhost:3000`

## 📡 API Endpoints

### Interview Management
- `POST /api/v1/interview/start` - Start new interview session
- `GET /api/v1/interview/{session_id}/status` - Get interview status
- `GET /api/v1/interview/{session_id}/question` - Get current question
- `POST /api/v1/interview/{session_id}/next-question` - Move to next question

### Interaction
- `POST /api/v1/interview/{session_id}/transcribe` - Transcribe audio to text
- `POST /api/v1/interview/{session_id}/submit-answer` - Submit text answer
- `POST /api/v1/interview/{session_id}/generate-followup` - Generate follow-up question

### System
- `GET /health` - Detailed health check
- `GET /` - System information

## 📁 Project Structure

```
AI_INTERVIEW_MVP/
├── backend/
│   ├── ai_backend/          # AI processing modules
│   │   ├── coordinator.py   # Main orchestrator
│   │   ├── speech_recognition/
│   │   ├── planner/         # Response analysis
│   │   └── chatbot/         # Follow-up generation
│   ├── api_gateway/         # API layer
│   ├── core/               # Shared utilities
│   └── main.py             # FastAPI application
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── utils/          # Utility functions
│   │   └── styles/         # CSS styles
│   └── package.json
├── README.md
└── CLAUDE.md              # Development guidelines
```

## 🌐 Browser Compatibility

### Voice Recognition Support
- ✅ **Chrome 25+** - Full voice support
- ✅ **Safari 14.1+** - Full voice support  
- ⚠️ **Firefox/Edge** - Text input fallback
- 📱 **Mobile** - Responsive design with voice support on compatible browsers

## 🧪 Testing

### Backend Testing
```bash
cd backend
pytest
```

### Frontend Testing
Currently using manual testing checklist (automated tests planned for future versions).

## 🚀 Deployment

### Backend Deployment
```bash
# Production server
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend Deployment
```bash
npm run build
# Deploy dist/ folder to your hosting service
```

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
- `VITE_API_URL` - Backend API URL (default: http://localhost:8000/api)

## 🔮 Future Enhancements

- [ ] Multi-language support
- [ ] Interview analytics and reporting
- [ ] Custom question templates
- [ ] Integration with HR systems
- [ ] Advanced AI coaching features
- [ ] Video interview support
- [ ] Automated test suite

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 🆘 Support

If you encounter any issues or have questions:

1. Check the [API documentation](http://localhost:8000/docs) when running locally
2. Review the troubleshooting section in `CLAUDE.md`
3. Open an issue on GitHub

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ using FastAPI, React, and OpenAI APIs**