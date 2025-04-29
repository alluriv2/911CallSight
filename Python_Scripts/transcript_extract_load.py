# %%
import re
import psycopg2
from sqlalchemy import create_engine
import csv
import pandas as pd
import json
import whisper
import os
import subprocess
import requests
from datetime import datetime
import psycopg2.extras


model = whisper.load_model("base")

os.environ["PATH"] = "/opt/homebrew/bin:" + os.environ["PATH"]


# %%
# Define PostgreSQL connection parameters

host = "localhost"       
port = "5432"       
database = "911_Call_Data"
user = "user_name"
password = "password"

conn = psycopg2.connect(database = database, user = user, host = host, password = password, port = port)

cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print('Connected to DB!')

# %%
####################################  Structure of the transcript json file  ####################################

# {
#   "date" : 'date'
#   "text": 'transcript'
#   "confidence_score": 'score'
# }

# %%
####################################  Creating transcript of all the files  ####################################

transcript_json = {}


folder_path = os.path.join(os.getcwd(), "..", "Audio_Files")

if not os.path.exists(folder_path):
    raise FileNotFoundError(f"Audio files folder not found at: {folder_path}")

audio_extensions = ('.mp3', '.wav', '.m4a', '.mp4')

for filename in os.listdir(folder_path):
    if filename.lower().endswith(audio_extensions):
        audio_path = os.path.join(folder_path, filename)
        print(f"Transcribing: {filename}")
        result = model.transcribe(audio_path)
        text = result["text"]

        segments = result.get("segments", [])
        logprobs = [seg["avg_logprob"] for seg in segments if "avg_logprob" in seg]

        if logprobs:
            avg_logprob = sum(logprobs) / len(logprobs)
            confidence_score = max(0.0, min(1.0, 1 + avg_logprob))  # crude map
        else:
            confidence_score = None


        transcript_json[filename.strip('.mp3')] = {
            "date" : datetime.strptime(filename[:8], "%Y%m%d").date().isoformat(),
            "text" : text.strip(),
            "confidence_score": round(confidence_score, 3) if confidence_score else None
            }


# Save transcription json of all files to one json file.
output_file = "all_transcripts.json"
with open(os.path.join(folder_path, output_file), "w") as f:
    json.dump(transcript_json, f, indent=3)

print(f"Transcripts saved to: {output_file}")

# %%
##################################  Function to get transcripts for date range  ##################################

json_file_path = os.path.join(os.getcwd(), "..", "Audio_Files", "all_transcripts.json")

if not os.path.exists(json_file_path):
    raise FileNotFoundError(f"File not found: {json_file_path}")


def getTranscript(start_date=None, end_date=None):
    with open(json_file_path, 'r') as f:
        transcripts = json.load(f)

    if start_date is not None:
        start_date = str(start_date)
    if end_date is not None:
        end_date = str(end_date)

    requested_transcripts = {}

    for key, value in transcripts.items():
        date_from_file = key[:8] 

        if start_date and end_date:
            if start_date <= date_from_file <= end_date:
                requested_transcripts[key] = value
        elif start_date:
            if date_from_file >= start_date:
                requested_transcripts[key] = value
        elif end_date:
            if date_from_file <= end_date:
                requested_transcripts[key] = value
        else:
            requested_transcripts[key] = value

    if not requested_transcripts:
        print("No transcripts found for the specified date(s).")

    return requested_transcripts
 

# %%
####################################  JSON Structure  ####################################

# {
#   "date" = date
#   "file": "file_name",
#   "raw_text": "Full original transcribed text here...",
#    "confidence_score": 0.92,
  
#   "incident_details": {
#     "incident_type": "Domestic / Medical / Fire / Suspicious Activity / Other",
#     "location": "123 Main St, City",
#     "time_reported": "21:07",
#     "reporting_party": "Caller / Driver / Neighbor / Unknown",
#     "urgency_level": "High / Medium / Low / Unknown"
#   },

#   "persons_involved": [
#     {
#       "role": "Victim / Suspect / Patient / Child",
#       "age": 21,
#       "gender": "Female",
#       "name": "Optional or Unknown"
#     }
#   ],

#   "medical_info": {
#     "vitals": {
#       "heart_rate": 120,
#       "blood_pressure": "120/90"
#     },
#     "symptoms": ["pinched nerve", "racing heart"],
#     "medications": ["methyl carbonate"]
#   },

#   "flags": {
#     "involves_children": True/False
#     "involves_weapons": True/False
#     "involves_drugs": True/False
#     "structure_fire": True/False
#     "domestic_dispute": True/False
#   },
# }

# %% [markdown]
# 

# %%
##################################  Function to get json from text using mistral (LLM Prompt)  ##################################

def mistral_json_extract(transcript_text):
    prompt = f"""
You are an expert emergency dispatch analyst and JSON specialist, highly familiar with the radio dispatch language used
by 911 operators.
Your task is to accurately extract structured information from transcripts into a strict JSON format exactly as shown below.

Instructions:
- Populate missing or unavailable information with `null`.
- Use only the provided fields exactly as named.
- Do not add or omit any fields.
- Do not add any explanatory text before or after the JSON output.
- Values must be clean and relevant — no extraneous words or phrases.
- If there is no information for the fields, do not leave it as blank. Populate it with null.
- All the below mentioned fields and subfields should be present in the output.
- If any field's subfield has no information, populate it as null.
- Return only the JSON object without any additional text, comments, or explanations.
- Ensure the field names and data types are strictly correct.
-Below is the JSON structure you must follow exactly. Descriptions for each field are provided to ensure accurate extraction.

- incident_details: General information about the emergency.
  - incident_type: The type of incident. Choose one: "Domestic", "Medical", "Fire", "Suspicious Activity", or "Other".
  - location: The location address of the incident. If unknown, use "Unknown".
  - time_reported: The time the incident was reported. If unavailable, use "Unknown".
  - reporting_party: Who reported the incident: "Caller", "Driver", "Neighbor", or "Unknown".
  - urgency_level: The urgency level: "High", "Medium", "Low", or "Unknown".

- persons_involved: List of people involved in the incident.
  - Each person must include:
    - role: Role of the person involved. Choose one: "Victim", "Suspect", "Patient", or "Child".
    - age: Age as an integer. If unknown, use null.
    - gender: Gender as "Male", "Female", or null if unknown.
    - name: Name of the person or "Unknown" if unavailable.

- medical_info: Medical data related to the incident.
  - vitals: Vital signs of the individual.
    - heart_rate: Heart rate value as an integer. Use null if unavailable.
    - blood_pressure: Blood pressure as a string (e.g., "120/90"). Use null if unavailable.
  - symptoms: A list of symptoms reported (e.g., ["chest pain", "shortness of breath"]).
  - medications: A list of medications reported (e.g., ["aspirin"]).

- flags: Boolean indicators for special conditions.
  - involves_children: true if children are involved, false otherwise.
  - involves_weapons: true if weapons are involved, false otherwise.
  - involves_drugs: true if drugs are involved, false otherwise.
  - structure_fire: true if a structural fire is involved, false otherwise.
  - domestic_dispute: true if it is a domestic dispute, false otherwise.

Here is the required JSON structure:

{{
  "incident_details": {{
    "incident_type": "Domestic / Medical / Fire / Suspicious Activity / Other",
    "location": "Address or Unknown",
    "time_reported": "Time or Unknown",
    "reporting_party": "Caller / Driver / Neighbor / Unknown",
    "urgency_level": "High / Medium / Low / Unknown"
  }},
  "persons_involved": [
    {{
      "role": "Victim / Suspect / Patient / Child",
      "age": 35,
      "gender": "Male",
      "name": "Optional or Unknown"
    }}
  ],
  "medical_info": {{
    "vitals": {{
      "heart_rate": 120,
      "blood_pressure": "120/90"
    }},
    "symptoms": ["chest pain", "shortness of breath"],
    "medications": ["aspirin"]
  }},
  "flags": {{
    "involves_children": true,
    "involves_weapons": false,
    "involves_drugs": false,
    "structure_fire": false,
    "domestic_dispute": true
  }}
}}

Transcript:
{transcript_text}

ONLY return the valid JSON output.
"""

    # Calling Ollama to run mistral 
    process = subprocess.Popen(
        ["ollama", "run", "mistral"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    output, error = process.communicate(input=prompt)

    try:
        
        match = re.search(r'\{.*\}',output,re.DOTALL)

        if match:
            output_clean = match.group()
            structured_json = json.loads(output_clean)
            return structured_json
        else:
            return None
        
    except Exception as e:
        print("Error parsing Mistral output:", e)
        print("Raw Mistral output:", output)
        return e

# %%
##################################  Creating master JSON  ##################################

emergency_calls_by_file = {}

emergency_calls_by_file = getTranscript()
        

for f_name in emergency_calls_by_file:
    print(f_name)
    print(emergency_calls_by_file[f_name])
    print(f"JSON Struct for {f_name}")
    json_extract = mistral_json_extract(emergency_calls_by_file[f_name].get('text'))
    print(json_extract)

    emergency_calls_by_file[f_name].update(json_extract)

# print(emergency_calls_by_file)
        

# %%
####################################  Creating emergency_calls table  ####################################

create_table_sql = '''DROP TABLE IF EXISTS emergency_calls; 
CREATE TABLE emergency_calls (
    call_id SERIAL PRIMARY KEY,
    call_date DATE,
    file_name VARCHAR(255),
    raw_text TEXT,
    confidence_score NUMERIC(4,3),

    incident_type VARCHAR(100),
    location TEXT,
    time_reported VARCHAR(20),
    reporting_party VARCHAR(100),
    urgency_level VARCHAR(20),

    person_role VARCHAR(50),
    person_age INTEGER,
    person_gender VARCHAR(20),
    person_name VARCHAR(100),

    heart_rate INTEGER,
    blood_pressure VARCHAR(20),
    symptoms TEXT,       
    medications TEXT,     

    involves_children BOOLEAN,
    involves_weapons BOOLEAN,
    involves_drugs BOOLEAN,
    structure_fire BOOLEAN,
    domestic_dispute BOOLEAN
);'''

cur.execute(create_table_sql)
conn.commit

print('Created emergency_calls table! ')

# %%
##################################  Verifying the insert  ##################################

for row in emergency_calls_by_file:
    print(emergency_calls_by_file[row].get('date'))
    print(row),
    print(emergency_calls_by_file[row].get('text')),
    print(emergency_calls_by_file[row].get('confidence_score')),
    print('\n')
    print(emergency_calls_by_file[row].get('incident_details').get('incident_type')),
    print(emergency_calls_by_file[row].get('incident_details').get('location')),
    print(emergency_calls_by_file[row].get('incident_details').get('time_reported')),
    print(emergency_calls_by_file[row].get('incident_details').get('reporting_party')),
    print(emergency_calls_by_file[row].get('incident_details').get('urgency_level')),
    print('\n')
    if len(emergency_calls_by_file[row].get('persons_involved')) > 0:
        print(emergency_calls_by_file[row].get('persons_involved')[0].get('role')), 
        print(emergency_calls_by_file[row].get('persons_involved')[0].get('age')), 
        print(emergency_calls_by_file[row].get('persons_involved')[0].get('gender')), 
        print(emergency_calls_by_file[row].get('persons_involved')[0].get('name'))
    else:
        print('No persons recorded.')

    print('\n')
    print(emergency_calls_by_file[row].get('medical_info').get('vitals').get('heart_rate')),
    print(emergency_calls_by_file[row].get('medical_info').get('vitals').get('blood_pressure')),
    print(emergency_calls_by_file[row].get('medical_info').get('symptoms')),
    print(emergency_calls_by_file[row].get('medical_info').get('medications')),

    print('\n')
    print(emergency_calls_by_file[row].get('flags').get('involves_children')), 
    print(emergency_calls_by_file[row].get('flags').get('involves_weapons')), 
    print(emergency_calls_by_file[row].get('flags').get('involves_drugs')), 
    print(emergency_calls_by_file[row].get('flags').get('structure_fire')), 
    print(emergency_calls_by_file[row].get('flags').get('domestic_dispute'))
    print('-----------------------------------')

# %%
##################################  Inserting info from master JSON to DB  ##################################

chunk_size = 1
chunk = []

for row in emergency_calls_by_file:
    if len(emergency_calls_by_file[row].get('persons_involved')) > 0:
        for persons in emergency_calls_by_file[row].get('persons_involved'):      
            chunk.append((
                emergency_calls_by_file[row].get('date'),
                row,
                emergency_calls_by_file[row].get('text'),
                emergency_calls_by_file[row].get('confidence_score'),
                emergency_calls_by_file[row].get('incident_details').get('incident_type'),
                emergency_calls_by_file[row].get('incident_details').get('location'),
                emergency_calls_by_file[row].get('incident_details').get('time_reported'),
                emergency_calls_by_file[row].get('incident_details').get('reporting_party'),
                emergency_calls_by_file[row].get('incident_details').get('urgency_level'),
                persons.get('role'), 
                persons.get('age'), 
                persons.get('gender'), 
                persons.get('name'),
                emergency_calls_by_file[row].get('medical_info').get('vitals').get('heart_rate'),
                emergency_calls_by_file[row].get('medical_info').get('vitals').get('blood_pressure'),
                ",".join(emergency_calls_by_file[row].get('medical_info').get('symptoms')),
                ",".join(emergency_calls_by_file[row].get('medical_info').get('medications')),
                emergency_calls_by_file[row].get('flags').get('involves_children'), 
                emergency_calls_by_file[row].get('flags').get('involves_weapons'), 
                emergency_calls_by_file[row].get('flags').get('involves_drugs'), 
                emergency_calls_by_file[row].get('flags').get('structure_fire'), 
                emergency_calls_by_file[row].get('flags').get('domestic_dispute')
                ))
    else:
        chunk.append((
            emergency_calls_by_file[row].get('date'),
            row,
            emergency_calls_by_file[row].get('raw_text'),
            emergency_calls_by_file[row].get('confidence_score'),
            emergency_calls_by_file[row].get('incident_details').get('incident_type'),
            emergency_calls_by_file[row].get('incident_details').get('location'),
            emergency_calls_by_file[row].get('incident_details').get('time_reported'),
            emergency_calls_by_file[row].get('incident_details').get('reporting_party'),
            None,
            None, 
            None, 
            None, 
            None,
            emergency_calls_by_file[row].get('medical_info').get('vitals').get('heart_rate'),
            emergency_calls_by_file[row].get('medical_info').get('vitals').get('blood_pressure'),
            ",".join(emergency_calls_by_file[row].get('medical_info').get('symptoms')),
            ",".join(emergency_calls_by_file[row].get('medical_info').get('medications')),
            emergency_calls_by_file[row].get('flags').get('involves_children'), 
            emergency_calls_by_file[row].get('flags').get('involves_weapons'), 
            emergency_calls_by_file[row].get('flags').get('involves_drugs'), 
            emergency_calls_by_file[row].get('flags').get('structure_fire'), 
            emergency_calls_by_file[row].get('flags').get('domestic_dispute')
        ))

    if len(chunk) >= chunk_size:
        data_insert_sql = '''
        INSERT INTO emergency_calls
        (
        call_date,
        file_name, 
        raw_text, 
        confidence_score,
        incident_type, 
        location, 
        time_reported, 
        reporting_party, 
        urgency_level,
        person_role, 
        person_age, 
        person_gender,
        person_name, 
        heart_rate, 
        blood_pressure, 
        symptoms, 
        medications, 
        involves_children,
        involves_weapons, 
        involves_drugs, 
        structure_fire, 
        domestic_dispute
        )

        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)

        '''

        try:
            cur.executemany(data_insert_sql,chunk)
        except Exception as e:
            print(f"Insert failed: {e}")
            conn.rollback()



        chunk.clear()
    
if len(chunk) > 0:
    cur.executemany(data_insert_sql,chunk)

    
conn.commit()






