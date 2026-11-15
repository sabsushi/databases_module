import os
from urllib.parse import urlparse

from pymongo import MongoClient
from pymongo.errors import OperationFailure

app_url = urlparse(os.environ["APP_MONGO_URL"])
user, password = app_url.username, app_url.password

admin = MongoClient(os.environ["MONGO_URL"])
db = admin["ex09"]
roles = [{"role": "readWrite", "db": "ex09"}]
if db.command("usersInfo", user)["users"]:
    db.command("updateUser", user, pwd=password, roles=roles)
    print(f"Updated MongoDB user {user}: readWrite on ex09")
else:
    db.command("createUser", user, pwd=password, roles=roles)
    print(f"Created MongoDB user {user}: readWrite on ex09")

app = MongoClient(os.environ["APP_MONGO_URL"])
app["ex09"]["notes"].find_one()
print("ex09_app can use ex09: OK")
try:
    app["other_db"]["x"].insert_one({"a": 1})
    print("ex09_app wrote to other_db: THIS SHOULD NOT HAPPEN")
except OperationFailure as e:
    print(f"ex09_app writing to other_db: refused ({e.details.get('codeName')})")
