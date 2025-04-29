# %%
import json, pymysql, time
from flask import Flask
from flask import request, redirect, jsonify
import psycopg2
import psycopg2.extras
from flask import jsonify



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
app = Flask(__name__)  

@app.route("/",methods = ['GET','POST'])
def root():
    return redirect('/home')


@app.route("/home",methods = ['GET','POST'])
def home():
    return '<html><b>Welcome!</b></html>'

# %%
#/getData?key={key}&start={start_date}&end={end_date}
@app.route("/getData",methods = ['GET','POST'])
def getData():
    res = {}
    if request.args.get('key') is None or request.args.get('key') != '123':
        res['data'] = None
        res['code'] = 0
        res['msg'] = 'invalid key'
        res['req'] = request.method
        return json.dumps(res,indent = 4)
    start = request.args.get('start')
    end = request.args.get('end')
    if start is None or end is None:
        res['data'] = None
        res['code'] = 0
        res['msg'] = 'dates not provided'
        res['req'] = request.method
        return json.dumps(res,indent = 4)
    
    sql = '''SELECT * FROM emergency_calls WHERE "call_date" BETWEEN %s AND %s ORDER BY "call_date" LIMIT 500 OFFSET 0;'''
    cur.execute(sql, (start, end)) 

    d = {}

    for row in cur:
        d[row['file_name']] = {
            "date": row['call_date'],
            "raw_text": row['raw_text'],
            "confidence_score": row['confidence_score'],

            "incident_details": {
                "incident_type": row['incident_type'],
                "location": row['location'],
                "time_reported": row['time_reported'],
                "reporting_party": row['reporting_party'],
                "urgency_level": row['urgency_level'] 
                },

            "persons_involved": [
                {
                    "role": row['person_role'],
                    "age": row['person_age'],
                    "gender": row['person_gender'],
                    "name": row['person_name']
                }
            ] if row['person_role'] else [],  
            "medical_info": {
                "vitals": {
                    "heart_rate": row['heart_rate'],
                    "blood_pressure": row['blood_pressure']
                },
                "symptoms": row['symptoms'].split(',') if row['symptoms'] else [],
                "medications": row['medications'].split(',') if row['medications'] else []
            },

            "flags": {
                "involves_children": row['involves_children'],
                "involves_weapons": row['involves_weapons'],
                "involves_drugs": row['involves_drugs'],
                "structure_fire": row['structure_fire'],
                "domestic_dispute": row['domestic_dispute']
            }
        }

    res['data'] = d
    res['code'] = 1
    res['msg'] = 'ok'
    res['req'] = request.method

    return jsonify(res)



    


# %%
if __name__ == "__main__":
    app.run(host = '127.0.0.1',debug = True)


