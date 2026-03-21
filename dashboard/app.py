import streamlit as st
import requests
import pandas as pd
from datetime import datetime

API_BASE = "http://localhost:8000/api/v1"

st.title("Face Recognition Attendance System - Admin Dashboard")

# User Registration
st.header("Register New User")
with st.form("register_form"):
    name = st.text_input("Name")
    employee_id = st.text_input("Employee ID")
    department = st.text_input("Department")
    role = st.selectbox("Role", ["student", "employee", "teacher", "admin"])
    frames = st.file_uploader("Upload 10 face images", accept_multiple_files=True, type=["jpg", "png"])
    submitted = st.form_submit_button("Register")
    if submitted:
        if len(frames) != 10:
            st.error("Exactly 10 images required")
        else:
            files = [("frames", (f.name, f, f.type)) for f in frames]
            data = {"name": name, "employee_id": employee_id, "department": department, "role": role}
            response = requests.post(f"{API_BASE}/users/register", data=data, files=files)
            if response.status_code == 200:
                st.success("User registered successfully")
            else:
                try:
                    error_obj = response.json()
                    st.error(error_obj)
                except Exception:
                    st.error(f"Registration failed ({response.status_code}): {response.text}")

# Attendance Report
st.header("Attendance Reports")
user_id = st.text_input("User ID (optional)")
session_id = st.text_input("Session ID (optional)")
if st.button("Fetch Reports"):
    params = {}
    if user_id:
        params["user_id"] = user_id
    if session_id:
        params["session_id"] = session_id
    response = requests.get(f"{API_BASE}/attendance/", params=params)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data)
        st.dataframe(df)
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "attendance.csv", "text/csv")
    else:
        st.error("Failed to fetch data")

# Live Camera Feed
st.header("Live Camera Feed")
st.write("Access the live camera stream with face recognition:")
stream_url = "http://localhost:8000/api/v1/camera/stream"
st.markdown(f"[Open Live Stream]({stream_url})")
st.write("**Note:** Open the link in a new tab to view the real-time feed.")
st.write("**To stop the separate camera window:** If you ran the camera script separately, press 'q' in the OpenCV window.")
st.write("The stream shows face detection, recognition, and attendance marking in real-time.")