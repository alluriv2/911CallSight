# %%
import json, pymysql, time
from flask import Flask
from flask import request, redirect
import requests
from sqlalchemy import create_engine
import psycopg2


# %%
url_getData = f'http://127.0.0.1:5000/getData?key=123&start=2025-04-02&end=2025-04-03'
output_getData = requests.get(url_getData)

# %%
print(json.dumps(output_getData.json(),indent=4))


