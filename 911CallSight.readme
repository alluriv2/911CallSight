# 911 Call Transcript Analysis & API Service

## Objective

To extract structured information from real-world 911 call transcriptions (generated using Whisper AI), store the data in a relational database, and expose it via an API for downstream analysis and search.

---

## Key Components

### 1. Data Ingestion
- Input: Short transcriptions of emergency calls
- Source: Whisper AI or pre-saved text
- Output: JSON objects capturing key fields (incident type, location, persons, medical info)

### 2. Data Structuring
- Convert free-text into structured JSON format
- Fields include:
  - Incident details (type, location, urgency)
  - Persons involved (role, age, gender)
  - Medical indicators
  - Binary flags (e.g., weapons, children involved)

### 3. Database Integration
- Relational table (`emergency_calls`)
- Flattened JSON values mapped to SQL columns
- Batch insertions with chunking for performance

### 4. REST API Service
- Built with Flask
- Endpoints:
  - `/calls`: Get latest 911 calls
  - `/calls/search?type=`: Filter by incident type
- Output: JSON-formatted query results from DB

---

## Example Use Case

Search for all calls labeled as "Domestic":