"""Delete test user via admin API so it can be recreated fresh."""
import sys
import json
import urllib.request
import urllib.error

def main():
    if len(sys.argv) < 4:
        print("Usage: cleanup_user.py <api_url> <admin_email> <admin_password> <user_email>")
        sys.exit(0)

    api_url = sys.argv[1]
    admin_email = sys.argv[2]
    admin_password = sys.argv[3]
    user_email = sys.argv[4]

    # Step 1: Login as admin to get token
    login_data = json.dumps({"email": admin_email, "password": admin_password}).encode("utf-8")
    login_req = urllib.request.Request(
        f"{api_url}/api/login",
        data=login_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(login_req) as resp:
            login_resp = json.loads(resp.read().decode("utf-8"))
            token = login_resp.get("token")
    except Exception as e:
        print(f"Admin login failed: {e}")
        sys.exit(0)  # Don't fail the test if cleanup can't happen

    # Step 2: Get all users to find user_id
    users_req = urllib.request.Request(
        f"{api_url}/api/admin/users",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="GET"
    )
    try:
        with urllib.request.urlopen(users_req) as resp:
            users = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Failed to get users: {e}")
        sys.exit(0)

    # Step 3: Find user by email
    user_id = None
    if isinstance(users, dict):
        users = users.get("users", [])
    for user in users:
        if isinstance(user, dict) and user.get("email") == user_email:
            user_id = user.get("user_id")
            break

    if not user_id:
        print(f"User {user_email} not found - nothing to delete")
        sys.exit(0)

    # Step 4: Delete user
    delete_req = urllib.request.Request(
        f"{api_url}/api/admin/user/{user_id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="DELETE"
    )
    try:
        with urllib.request.urlopen(delete_req) as resp:
            result = resp.read().decode("utf-8")
            print(f"Deleted user {user_email}: {result}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"Delete failed ({e.code}): {body}")
    except Exception as e:
        print(f"Delete failed: {e}")

if __name__ == "__main__":
    main()
