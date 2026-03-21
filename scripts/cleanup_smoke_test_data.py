from app.db.firebase_client import get_firestore


def delete_query_docs(collection_ref, field, op, value):
    docs = list(collection_ref.where(field, op, value).stream())
    for doc in docs:
        doc.reference.delete()
    return len(docs)


def main():
    db = get_firestore()

    users_deleted = 0
    periods_deleted = 0
    period_attendance_deleted = 0
    notifications_deleted = 0
    scheduler_runs_deleted = 0

    # Delete users created by smoke test
    smoke_users = list(db.collection("users").where("createdBy", "==", "smoke-test").stream())
    smoke_user_ids = [doc.id for doc in smoke_users]
    for doc in smoke_users:
        doc.reference.delete()
    users_deleted += len(smoke_users)

    # Delete teachers created by smoke-test naming pattern TCHRxxxxxx
    teacher_docs = list(db.collection("users").where("employeeId", ">=", "TCHR").where("employeeId", "<", "TCHS").stream())
    for doc in teacher_docs:
        data = doc.to_dict() or {}
        emp = str(data.get("employeeId", ""))
        email = str(data.get("email", ""))
        if emp.startswith("TCHR") and "@example.com" in email:
            doc.reference.delete()
            users_deleted += 1

    # Delete test periods with name prefix Period- and class prefix class_
    period_docs = list(db.collection("periods").stream())
    deleted_period_ids = []
    for doc in period_docs:
        data = doc.to_dict() or {}
        name = str(data.get("name", ""))
        class_id = str(data.get("classId", ""))
        if name.startswith("Period-") and class_id.startswith("class_"):
            deleted_period_ids.append(data.get("periodId") or doc.id)
            doc.reference.delete()
            periods_deleted += 1

    # Delete periodAttendance docs linked to deleted periods or smoke users
    patt_docs = list(db.collection("periodAttendance").stream())
    for doc in patt_docs:
        data = doc.to_dict() or {}
        if data.get("periodId") in deleted_period_ids or data.get("userId") in smoke_user_ids:
            doc.reference.delete()
            period_attendance_deleted += 1

    # Delete absenceNotifications linked to deleted periods or smoke users
    notif_docs = list(db.collection("absenceNotifications").stream())
    for doc in notif_docs:
        data = doc.to_dict() or {}
        if data.get("periodId") in deleted_period_ids or data.get("userId") in smoke_user_ids:
            doc.reference.delete()
            notifications_deleted += 1

    # Delete scheduler run logs linked to deleted periods
    run_docs = list(db.collection("periodSchedulerRuns").stream())
    for doc in run_docs:
        data = doc.to_dict() or {}
        if data.get("periodId") in deleted_period_ids:
            doc.reference.delete()
            scheduler_runs_deleted += 1

    print({
        "users_deleted": users_deleted,
        "periods_deleted": periods_deleted,
        "period_attendance_deleted": period_attendance_deleted,
        "notifications_deleted": notifications_deleted,
        "scheduler_runs_deleted": scheduler_runs_deleted,
    })


if __name__ == "__main__":
    main()
