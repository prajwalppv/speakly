# Speakly Build Plan

## Overview

This document outlines the detailed 3-phased build plan for the Speakly app. Speakly is a voice-based application designed with a modern, scalable architecture and a robust tech stack. The plan includes finalized choices for the technology stack, architecture, data model, APIs, and workflows.

---

## Phase 1: Scaffolding Hello Pipeline

### Objectives

- Set up the foundational infrastructure and project scaffolding.
- Establish a minimal viable pipeline to process audio input and generate a basic response.
- Implement basic API endpoints and frontend integration to validate the pipeline.

### Technology Stack

- **Backend:** FastAPI
- **Frontend:** React with Vite
- **Database:** SQLite (initial setup)
- **Audio Storage:** Local file system
- **Logging:** JSON logs for requests and errors

### Tasks

1. **Project Initialization**
   - Initialize FastAPI backend project.
   - Initialize React + Vite frontend project.
   - Setup SQLite database schema for basic app data (users, sessions).

2. **API Development**
   - Create a simple API endpoint to accept audio uploads.
   - Store audio files locally.
   - Return a basic JSON response confirming receipt.

3. **Frontend Integration**
   - Build a simple React interface to record or upload audio.
   - Connect frontend with backend API to send audio data.
   - Display the backend response on the UI.

4. **Logging and Error Handling**
   - Implement JSON structured logging for API requests and errors.
   - Define a consistent error response shape.

5. **Testing & Validation**
   - Validate end-to-end flow from frontend audio submission to backend response.
   - Ensure SQLite integration and local audio storage functionality.

---

## Phase 2: Core Functionality with ElevenLabs + SQLite

### Objectives

- Integrate ElevenLabs Scribe STT for speech-to-text transcription using async webhooks.
- Develop core backend logic to handle transcription results and process them.
- Expand database schema to support transcription data and user sessions.
- Improve frontend to display transcription results and basic interaction.

### Technology Stack

- **Backend:** FastAPI with async webhook handling
- **Frontend:** React + Vite
- **Speech-to-Text:** ElevenLabs Scribe STT (async webhook model)
- **Database:** SQLite (expanded schema)
- **Audio Storage:** Local file system
- **Logging:** JSON logs and error shape maintained

### Tasks

1. **ElevenLabs Integration**
   - Implement async webhook endpoints to receive transcription results.
   - Handle webhook verification and security.
   - Store transcription text and metadata in SQLite.

2. **Backend Processing**
   - Process transcription results to prepare for further NLP tasks.
   - Maintain session and conversation state in the database.

3. **Frontend Enhancements**
   - Display real-time or near-real-time transcription results.
   - Allow users to review and interact with transcriptions.

4. **API Enhancements**
   - Add endpoints to fetch transcription history and session data.
   - Improve error handling around webhook and transcription failures.

5. **Testing & Validation**
   - Test full pipeline: audio upload → transcription → display.
   - Validate webhook handling and database updates.

---

## Phase 3: MVP+ with Diarization, PJ Voice ID, Filters

### Objectives

- Add advanced features such as speaker diarization and personalized voice identification.
- Implement filters and enhanced interaction capabilities.
- Integrate Ollama as the default Large Language Model (LLM) for NLP tasks.
- Refine data model and workflows for production readiness.

### Technology Stack

- **Backend:** FastAPI
- **Frontend:** React + Vite
- **Speech-to-Text:** ElevenLabs Scribe STT
- **LLM:** Ollama (default)
- **Database:** SQLite (finalized schema)
- **Audio Storage:** Local
- **Workflow Automation:** n8n using SQLite
- **Logging:** JSON logs and error shape

### Tasks

1. **Speaker Diarization**
   - Integrate diarization to distinguish between multiple speakers in audio.
   - Store diarization metadata alongside transcriptions.

2. **PJ Voice ID**
   - Implement voice identification for the user "PJ" to personalize experience.
   - Use voice ID to tag and filter conversations.

3. **Filters and Interaction**
   - Develop filters for transcription and conversation data (e.g., by speaker, date).
   - Enhance frontend UI for advanced filtering and search.

4. **Ollama LLM Integration**
   - Connect backend with Ollama for NLP and conversational AI tasks.
   - Use LLM to generate responses, summaries, or insights from transcriptions.

5. **n8n Workflow Automation**
   - Setup n8n workflows to automate data processing and integrations.
   - Use SQLite as the backend for n8n workflows.

6. **Final Data Model and API Refinements**
   - Finalize database schema to support diarization, voice ID, and filters.
   - Harden API endpoints for production use.

7. **Testing, Security, and Deployment**
   - Comprehensive testing of all features.
   - Implement security best practices for webhooks, APIs, and data storage.
   - Prepare deployment configurations.

---

## Summary

| Phase | Focus                                | Key Technologies                         |
|-------|------------------------------------|----------------------------------------|
| 1     | Scaffolding hello pipeline          | FastAPI, React + Vite, SQLite, Local Storage |
| 2     | Core functionality with ElevenLabs | ElevenLabs Scribe STT, Async Webhooks, SQLite, React |
| 3     | MVP+ with diarization and filters   | Ollama LLM, Diarization, PJ Voice ID, n8n, SQLite, React |

This phased approach ensures a stable foundation before adding advanced features, enabling iterative development and testing. The chosen stack provides flexibility, scalability, and a clean separation of concerns for the Speakly app.
