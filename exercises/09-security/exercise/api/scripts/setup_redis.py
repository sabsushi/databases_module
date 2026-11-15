import os
from urllib.parse import urlparse

import redis

app_url = urlparse(os.environ["APP_REDIS_URL"])
user, password = app_url.username, app_url.password

admin = redis.Redis.from_url(os.environ["REDIS_URL"])
admin.execute_command(
    "ACL", "SETUSER", user, "reset", "on", f">{password}",
    "~counter:*", "+@all", "-@dangerous",
)
print(f"ACL SETUSER {user} on >*** ~counter:* +@all -@dangerous")

app = redis.Redis.from_url(os.environ["APP_REDIS_URL"], decode_responses=True)
print("whoami:", app.acl_whoami())
print("INCR counter:setup_test ->", app.incr("counter:setup_test"))
app.delete("counter:setup_test")
for name, call in [
    ("SET other:key 1", lambda: app.set("other:key", 1)),
    ("FLUSHALL", lambda: app.flushall()),
    ("KEYS *", lambda: app.keys("*")),
]:
    try:
        call()
        print(f"{name}: allowed (THIS SHOULD NOT HAPPEN)")
    except redis.exceptions.NoPermissionError as e:
        print(f"{name}: refused: {e}")
