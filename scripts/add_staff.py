import argparse
import uuid
from datetime import datetime

from passlib.context import CryptContext

from app.db.firebase_client import get_firestore


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def main():
    parser = argparse.ArgumentParser(description="Bootstrap first staff/admin account")
    parser.add_argument("--staff-id", required=True, help="Unique staff ID used for login")
    parser.add_argument("--name", required=True, help="Staff full name")
    parser.add_argument("--pin", required=True, help="Numeric/alphanumeric login PIN")
    parser.add_argument("--role", default="admin", choices=["staff", "admin", "teacher", "employee"], help="Staff role")
    parser.add_argument("--email", default=None, help="Optional email")
    parser.add_argument("--department", default="college", help="Department name")
    args = parser.parse_args()

    db = get_firestore()
    existing = list(db.collection("users").where("employeeId", "==", args.staff_id).limit(1).stream())
    if existing:
        print(f"Staff ID already exists: {args.staff_id}")
        return

    user_id = str(uuid.uuid4())
    data = {
        "userId": user_id,
        "employeeId": args.staff_id,
        "name": args.name,
        "department": args.department,
        "role": args.role,
        "email": args.email,
        "registeredAt": datetime.utcnow(),
        "isActive": True,
        "isOnboarded": True,
        "uploadedImageCount": 0,
        "embeddingDim": 0,
        "pinHash": pwd_context.hash(args.pin),
        "createdBy": "bootstrap-script",
    }

    db.collection("users").document(user_id).set(data)
    print("Staff account created")
    print(f"userId: {user_id}")
    print(f"staffId: {args.staff_id}")
    print(f"role: {args.role}")


if __name__ == "__main__":
    main()
