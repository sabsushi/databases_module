import os
from contextlib import asynccontextmanager
from typing import Annotated

import psycopg
import redis
from fastapi import FastAPI, Path
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr
from pymongo import MongoClient

APP_DATABASE_URL = os.environ["APP_DATABASE_URL"]
APP_MONGO_URL = os.environ["APP_MONGO_URL"]
APP_REDIS_URL = os.environ["APP_REDIS_URL"]

mongo = MongoClient(APP_MONGO_URL)
notes = mongo["ex09"]["notes"]
r = redis.Redis.from_url(APP_REDIS_URL, decode_responses=True)

@asynccontextmanager
async def lifespan(app):
    yield
    mongo.close()
    r.close()

app = FastAPI(title="Exercise 09: security", lifespan=lifespan)

class ActorIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: StrictStr
    last_name: StrictStr

class NoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_id: StrictInt
    text: StrictStr

@app.post("/actors", status_code=201)
def create_actor(body: ActorIn):
    with psycopg.connect(APP_DATABASE_URL) as conn:
        actor_id = conn.execute(
            "INSERT INTO actor (first_name, last_name) VALUES (%s, %s) RETURNING actor_id",
            (body.first_name, body.last_name),
        ).fetchone()[0]
    return {"actor_id": actor_id}

@app.post("/notes", status_code=201)
def create_note(body: NoteIn):
    result = notes.insert_one({"customer_id": body.customer_id, "text": body.text})
    return {"id": str(result.inserted_id)}

CounterName = Annotated[str, Path(pattern=r"^[a-z0-9_-]{1,32}$")]

@app.post("/counters/{name}")
def increment_counter(name: CounterName):
    return {"name": name, "value": r.incr(f"counter:{name}")}
