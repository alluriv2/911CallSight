# 911CallSight

## Table of Contents
- [Project Overview](#project-overview)
- [Technologies Used](#technologies-used)
- [Project Workflow](#project-workflow)
  - [Audio Transcription](#audio-transcription)
  - [Structured Information Extraction](#structured-information-extraction)
  - [Data Loading into PostgreSQL](#data-loading-into-postgresql)
  - [Flask API Development](#flask-api-development)
  - [API Client Example](#api-client-example)
- [API Documentation](#api-documentation)
- [Setup Instructions](#setup-instructions)
  - [Python Requirements](#python-requirements)
  - [Model Setup (Mistral via Ollama)](#model-setup-mistral-via-ollama)
- [Future Enhancements](#future-enhancements)


---

## Project Overview

This project builds a full pipeline for processing emergency 911 call recordings, including transcription, structured data extraction, database storage, and API access for querying the data.

---

## Technologies Used

- Python 3.12
- PostgreSQL
- Flask
- Whisper ASR model (via `openai-whisper`)
- Mistral LLM (via [Ollama](https://ollama.com/))
- psycopg2 and SQLAlchemy
- Requests for API integration

---

## Project Workflow

### Audio Transcription

- Transcribes `.mp3`, `.wav`, `.m4a`, and `.mp4` files using Whisper.
- Calculates a confidence score based on log probabilities.
- Saves all transcripts to `Audio_Files/all_transcripts.json`.

### Structured Information Extraction

- Uses a structured prompt and Mistral (LLM via Ollama) to extract:
  - Incident details
  - Persons involved
  - Medical information
  - Boolean condition flags
- Enforces schema with `null` fallbacks for missing values.

### Data Loading into PostgreSQL

- A PostgreSQL database `911_Call_Data` is created.
- A table `emergency_calls` is created with fields matching the extracted JSON schema.
- Transcription and extracted data are inserted into the database.

### Flask API Development

- A Flask server exposes APIs to retrieve data.
- Routes:
  - `/` → Redirects to `/home`
  - `/home` → Simple welcome page
  - `/getData` → API to fetch emergency call data between given dates

### API Client Example

- Sample Python client demonstrates calling `/getData` using `requests` and printing formatted output.

---

## API Documentation

### `/getData` Endpoint

**URL:**  
`http://127.0.0.1:5000/getData?key={key}&start={start_date}&end={end_date}`

**Request Method:**  
- GET
- POST

**Query Parameters:**

| Parameter | Required | Description |
|:----------|:---------|:------------|
| key       | Yes      | API authentication key (`123`) |
| start     | Yes      | Start date in `YYYY-MM-DD` format |
| end       | Yes      | End date in `YYYY-MM-DD` format |

**Success Response:**

- **Code:** 200 OK
- **Content:** JSON object containing 911 call data grouped by file name.

Example response:

```json
{
    "data": {
        "20250402165948_20250402170016_1_2": {
            "date": "2025-04-02",
            "raw_text": "Transcribed emergency call text",
            "confidence_score": 0.926,
            "incident_details": { ... },
            "persons_involved": [...],
            "medical_info": { ... },
            "flags": { ... }
        }
    },
    "code": 1,
    "msg": "ok",
    "req": "GET"
}
```

**Error Responses:**

- Invalid API Key
- Missing start or end dates
- No data found for the specified date range

---

## Setup Instructions

1. Install required Python libraries:

```bash
pip install flask psycopg2 whisper requests
```

2. Install [ffmpeg](https://ffmpeg.org/) — required by Whisper for audio processing:

```bash
brew install ffmpeg  # MacOS
# or
sudo apt install ffmpeg  # Linux
```

3. Set up [Ollama](https://ollama.com/) to run local LLMs:

- Download and install Ollama from [https://ollama.com](https://ollama.com).
- Once installed, open a terminal and run:

```bash
ollama run mistral
```

This will pull the Mistral model and start serving it locally.

4. Start PostgreSQL database server and create a database named `911_Call_Data`.

5. Create the `emergency_calls` table using the provided SQL schema.

6. Place audio files into the `Audio_Files/` folder (use `../Audio_Files/` if running from a `Notebooks/` directory).

7. Run the transcription and structured information extraction script to:

- Transcribe 911 audio using **Whisper**
- Extract structured JSON using **Mistral via Ollama**
- Save all transcripts in a file called `all_transcripts.json`

8. Insert data into PostgreSQL using the provided database script.

9. Launch the Flask server:

```bash
python flask_app_main.py
```

10. Access the API through your browser, Postman, or a Python script.

---

## Future Enhancements

- Implement authentication tokens instead of static keys.
- Add pagination support to the `/getData` API.
- Deploy the Flask server using Gunicorn and Nginx for production.
- Implement error logging and monitoring.
- Extend the database schema to store call duration and transcription timestamps.

---