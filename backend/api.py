import fastapi
from fastapi import FastAPI
from .. import database

app = FastAPI()




@app.get('/feed')
def get_feed():
    pass 