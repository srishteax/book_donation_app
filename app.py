import streamlit as st
import pandas as pd
import os
import csv
from fuzzywuzzy import fuzz
from geopy.geocoders import Nominatim

# File paths
DONORS_CSV = "donors.csv"
REQUESTS_CSV = "requests.csv"
USERS_CSV = "users.csv"
BOOK_IMAGES = "book_images"
os.makedirs(BOOK_IMAGES, exist_ok=True)
for f in [DONORS_CSV, REQUESTS_CSV, USERS_CSV]:
    if not os.path.exists(f):
        open(f, "w").close()

# Geolocator
geolocator = Nominatim(user_agent="book_donation_app")

def get_coordinates(city):
    try:
        location = geolocator.geocode(city)
        if location:
            return location.latitude, location.longitude
    except:
        pass
    return None, None

def save_user(username, password, role):
    with open(USERS_CSV, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([username, password, role])

def validate_user(username, password):
    if not os.path.exists(USERS_CSV):
        return None
    with open(USERS_CSV, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row and row[0] == username and row[1] == password:
                return row[2]
    return None

def compute_matches():
    try:
        df_d = pd.read_csv(DONORS_CSV, names=["user","book","subject","grade","cond","city","email","img","lat","lon"])
        df_r = pd.read_csv(REQUESTS_CSV, names=["user","subject","grade","city","urgency","email","lat","lon"])
        matches = []
        for _, r in df_r.iterrows():
            for _, d in df_d.iterrows():
                if r["grade"] == d["grade"] and r["city"].strip().lower() == d["city"].strip().lower():
                    score = fuzz.token_sort_ratio(str(r["subject"]), str(d["subject"]))
                    if score > 80:
                        matches.append({**r.to_dict(), **d.to_dict(), "score": score})
        return pd.DataFrame(matches)
    except:
        return pd.DataFrame()

def login_screen():
    st.title("🔐 Login")
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            role = validate_user(username, password)
            if role:
                st.session_state.logged_in = True
                st.session_state.current_user = username
                st.session_state.current_role = role
                st.success(f"Welcome, {username} ({role})")
                st.rerun()
            else:
                st.error("Invalid credentials")

def register_screen():
    st.title("📝 Register")
    with st.form("register_form", clear_on_submit=True):
        username = st.text_input("Choose a username")
        password = st.text_input("Choose a password", type="password")
        role = st.selectbox("Select your role", ["Donor", "Receiver", "Admin"])
        submitted = st.form_submit_button("Register")
        if submitted:
            save_user(username, password, role)
            st.success("Registration successful. Please login.")
            st.rerun()

def show_dashboard():
    role = st.session_state.current_role
    st.sidebar.write(f"👤 {st.session_state.current_user} ({role})")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    if role == "Admin":
        st.title("🛠️ Admin Dashboard")
        tab = st.radio("Select Panel", ["Donors", "Requests", "Users", "Analytics"])

        if tab == "Donors":
            df = pd.read_csv(DONORS_CSV, names=["user","book","subject","grade","condition","city","email","img","lat","lon"])
            st.dataframe(df)

        elif tab == "Requests":
            df = pd.read_csv(REQUESTS_CSV, names=["user","subject","grade","city","urgency","email","lat","lon"])
            st.dataframe(df)

        elif tab == "Users":
            df = pd.read_csv(USERS_CSV, names=["username","password","role"])
            st.dataframe(df.drop(columns=["password"]))

        elif tab == "Analytics":
            donors = pd.read_csv(DONORS_CSV, names=["user","book","subject","grade","condition","city","email","img","lat","lon"])
            requests = pd.read_csv(REQUESTS_CSV, names=["user","subject","grade","city","urgency","email","lat","lon"])
            st.metric("Total Donations", len(donors))
            st.metric("Total Requests", len(requests))
            st.bar_chart(donors["subject"].value_counts())
            st.bar_chart(requests["subject"].value_counts())

    elif role == "Donor":
        st.title("📚 Donor Dashboard")
        with st.form("donate_form"):
            book = st.text_input("Book Name")
            subject = st.text_input("Subject")
            grade = st.selectbox("Grade", [str(i) for i in range(1, 13)])
            cond = st.selectbox("Condition", ["New", "Good", "Worn"])
            city = st.text_input("City")
            email = st.text_input("Email")
            img = st.file_uploader("Upload Book Image")
            submit = st.form_submit_button("Donate")

            if submit:
                lat, lon = get_coordinates(city)
                img_path = os.path.join(BOOK_IMAGES, img.name) if img else ""
                if img:
                    with open(img_path, "wb") as f:
                        f.write(img.read())
                df = pd.DataFrame([[st.session_state.current_user, book, subject, grade, cond, city, email, img_path, lat, lon]])
                df.to_csv(DONORS_CSV, mode='a', header=False, index=False)
                st.success("Donation submitted!")
                if lat and lon:
                    st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}))

    elif role == "Receiver":
        st.title("📥 Receiver Dashboard")
        with st.form("request_form"):
            subject = st.text_input("Subject")
            grade = st.selectbox("Grade", [str(i) for i in range(1, 13)])
            city = st.text_input("City")
            urgency = st.selectbox("Urgency", ["Low", "Medium", "High"])
            email = st.text_input("Email")
            submit = st.form_submit_button("Request Book")

            if submit:
                lat, lon = get_coordinates(city)
                df = pd.DataFrame([[st.session_state.current_user, subject, grade, city, urgency, email, lat, lon]])
                df.to_csv(REQUESTS_CSV, mode='a', header=False, index=False)
                st.success("Request submitted!")
                if lat and lon:
                    st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}))

        matches = compute_matches()
        if not matches.empty:
            st.subheader("🔍 Book Matches")
            st.dataframe(matches[["user", "book", "subject", "grade", "city", "email", "score"]])
        else:
            st.info("No matches found yet.")

# App start
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if not st.session_state.logged_in:
    choice = st.sidebar.selectbox("Login or Register", ["Login", "Register"])
    if choice == "Login":
        login_screen()
    else:
        register_screen()
else:
    show_dashboard()