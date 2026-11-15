import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(
    page_title="Esone",
    page_icon="🔒",
    layout="wide"
)

API_URL = st.secrets.get("API_URL", "http://localhost:8000")

def register():
    st.title("Create your account")
    st.write("Pick a username, add your email and choose a strong password.")
    
    username = st.text_input("Username", placeholder="your-handle")
    email = st.text_input("Email", placeholder="you@company.com")
    password = st.text_input("Password", type="password", placeholder="At least 8 characters")
    confirm = st.text_input("Confirm password", type="password", placeholder="Repeat your password")
    
    if st.button("Create account"):
        if len(username) < 3:
            st.error("Username must have 3+ characters")
            return
        if "@" not in email:
            st.error("Invalid email")
            return
        if len(password) < 8:
            st.error("Password must have 8+ characters")
            return
        if password != confirm:
            st.error("Passwords don't match")
            return
        
        try:
            response = requests.post(f"{API_URL}/api/v1/auth/register", json={
                "username": username,
                "email": email,
                "password": password
            })
            if response.status_code == 201:
                st.success("Account created! You can now sign in.")
                st.session_state.page = "login"
            else:
                st.error(f"Registration failed: {response.text}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

def login():
    st.title("Welcome back")
    st.write("Sign in with your Esone username and password.")
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Sign in"):
        try:
            response = requests.post(f"{API_URL}/api/v1/auth/login", json={
                "username": username,
                "password": password
            })
            if response.status_code == 200:
                data = response.json()
                st.session_state.access_token = data.get("access_token")
                st.session_state.refresh_token = data.get("refresh_token")
                st.success("Signed in successfully!")
                st.session_state.page = "account"
            else:
                st.error("Invalid credentials")
        except Exception as e:
            st.error(f"Error: {str(e)}")

def account():
    st.title("Account")
    
    if st.button("Sign out"):
        st.session_state.clear()
        st.session_state.page = "login"
        st.rerun()
    
    st.subheader("Session Info")
    if st.session_state.get("access_token"):
        st.text(st.session_state.access_token)

def main():
    if "page" not in st.session_state:
        st.session_state.page = "index"
    
    page = st.session_state.page
    
    st.sidebar.title("Esone")
    if st.sidebar.button("Home"):
        st.session_state.page = "index"
        st.rerun()
    if st.sidebar.button("Register"):
        st.session_state.page = "register"
        st.rerun()
    if st.sidebar.button("Login"):
        st.session_state.page = "login"
        st.rerun()
    if st.sidebar.button("Account"):
        st.session_state.page = "account"
        st.rerun()
    
    if page == "register":
        register()
    elif page == "login":
        login()
    elif page == "account":
        account()
    else:
        st.title("Esone")
        st.write("Authentication platform")
        st.write("Sign-in that is simple to trust.")
        st.write("Esone issues short-lived access tokens, rotates refresh tokens, tags every session with a role.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create account"):
                st.session_state.page = "register"
                st.rerun()
        with col2:
            if st.button("Sign in"):
                st.session_state.page = "login"
                st.rerun()

if __name__ == "__main__":
    main()
