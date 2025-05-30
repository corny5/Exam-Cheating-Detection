# Exam Cheating Detection System

A real-time system for detecting potential cheating behaviors during exams using computer vision and machine learning.

## Features

- Real-time webcam monitoring
- Detection of suspicious behaviors:
  - Looking at other student's papers
  - Using phones or unauthorized devices
  - Talking or whispering
  - Passing notes
- Local PostgreSQL storage for detected events
- Web interface for monitoring and alerts

## Prerequisites

- Python 3.12+
- PostgreSQL
- Webcam
- CUDA-capable GPU (recommended for better performance)

## Installation

1. Create and activate a virtual environment:

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. Install required packages:

   ```powershell
   pip install -r requirements.txt
   ```

3. Initialize the PostgreSQL database:

   ```powershell
   .\init_db.ps1
   ```

4. Configure the environment variables in `.env` file:

   - Set your PostgreSQL credentials
   - Adjust detection thresholds if needed

   Example `.env` template:

   ```env
   # Database Configuration
   DB_NAME=cheating_detection
   DB_USER=postgres
   DB_PASSWORD=Mypostgres@123
   DB_HOST=localhost
   DB_PORT=5432

   # Application Configuration
   SAVE_FRAMES_DIR=detected_frames
   DETECTION_CONFIDENCE=0.6
   ALERT_THRESHOLD=0.7
   ```

## Usage

1. Start the application:

   ```powershell
   python app.py
   ```

2. Open your web browser and navigate to `http://localhost:5000`

3. The system will:
   - Show the live webcam feed
   - Display real-time alerts for detected behaviors
   - Store detection events in the database

## Note

This is a prototype system designed for local use in small classroom settings (5-10 students). It runs entirely offline and stores all data locally.
