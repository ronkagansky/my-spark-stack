# Prompt Stack 🚀

> Prompt Stack is an tool for building web applications through an AI-powered chat interface. Create quick MVPs and prototypes using natural language prompts.

<img width="800" alt="chrome_vMZlrhHm0u" src="https://github.com/user-attachments/assets/4c1912c9-85c9-4169-9d6c-bb5f96edd23e">

## Features

- 🤖 AI-powered code generation
- ⚡️ Real-time development environment
- 🎨 Multiple arbitrary starter templates (see `/images`)
- 👥 Team collaboration
- 📝 Git version control
- 🔄 Live preview

## Setup

### Environment Configuration

See `backend/config.py` for the environment variables that are used to configure the app.

- Requires modal account to be created and configured.
- Requires AWS account and s3 bucket to be configured.

### Development

- `cd frontend && npm install && npm run dev`
- `cd backend && pip install -r requirements.txt && python main.py`

### Deployment

Railway (docker + postgres).

<img width="200" alt="chrome_E9GXwtsE87" src="https://github.com/user-attachments/assets/b45e70f7-a8c5-426b-8dda-c5ae42da54c0">
