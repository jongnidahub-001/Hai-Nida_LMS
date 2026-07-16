import requests
import json

base = "http://localhost:5000"

# Login as admin
r = requests.post(f"{base}/api/login", json={"email": "admin@admin.com", "password": "admin"})
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Get all users
r2 = requests.get(f"{base}/api/admin/users", headers=headers)
data = r2.json()
print(f"Type: {type(data)}")
if isinstance(data, dict):
    users = data.get("users", data.get("data", []))
    print(f"Keys: {data.keys()}")
else:
    users = data
    
print(f"\nUsers ({len(users)}):")
for u in users[:10]:
    if isinstance(u, dict):
        print(f"  {u.get('email')} - is_auth={u.get('is_auth')} - role={u.get('role')}")
    else:
        print(f"  {u}")

# Try login with default pwd
print("\nLogin test:")
r3 = requests.post(f"{base}/api/login", json={"email": "testuser@robot.com", "password": "haionetime1234"})
print(f"  Status: {r3.status_code}, Body: {r3.text[:200]}")
