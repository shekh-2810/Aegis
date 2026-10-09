"""
Creates (or resets) a known test account so login can be tested immediately
without going through signup first.

    python create_test_user.py

Test credentials (also printed when this runs):
    email:    test@example.com
    password: Test@1234

Safe to re-run — if the account already exists, this just resets its
password back to the one above instead of erroring out.
"""

from auth_utils import hash_password
from database import users_collection

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "Test@1234"
TEST_NAME = "Test User"


def main():
    existing = users_collection.find_one({"email": TEST_EMAIL})
    password_hash = hash_password(TEST_PASSWORD)

    if existing:
        users_collection.update_one(
            {"_id": existing["_id"]},
            {"$set": {"password_hash": password_hash, "name": TEST_NAME}},
        )
        print(f"Test user already existed — password reset.")
    else:
        users_collection.insert_one(
            {"name": TEST_NAME, "email": TEST_EMAIL, "password_hash": password_hash}
        )
        print(f"Test user created.")

    print()
    print("  email:    ", TEST_EMAIL)
    print("  password: ", TEST_PASSWORD)
    print()
    print("Log in with these at frontend/login.html to test the dashboard, report wizard, etc.")


if __name__ == "__main__":
    main()
