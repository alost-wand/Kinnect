import requests
import streamlit as st

BASE_URL = "http://localhost:8000"

def get_headers(need_auth=True):
    headers = {}
    if need_auth and st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    return headers

class APIClient:
    @staticmethod
    def post(endpoint, data=None, json=None, files=None, need_auth=True):
        headers = get_headers(need_auth=need_auth)
        try:
            return requests.post(f"{BASE_URL}{endpoint}", data=data, json=json, files=files, headers=headers)
        except Exception as e:
            st.error(f"Connection error to backend: {e}")
            return None

    @staticmethod
    def get(endpoint, params=None, need_auth=True):
        headers = get_headers(need_auth=need_auth)
        try:
            return requests.get(f"{BASE_URL}{endpoint}", params=params, headers=headers)
        except Exception as e:
            st.error(f"Connection error to backend: {e}")
            return None

    @staticmethod
    def patch(endpoint, json=None, need_auth=True):
        headers = get_headers(need_auth=need_auth)
        try:
            return requests.patch(f"{BASE_URL}{endpoint}", json=json, headers=headers)
        except Exception as e:
            st.error(f"Connection error to backend: {e}")
            return None

    @staticmethod
    def delete(endpoint, params=None, need_auth=True):
        headers = get_headers(need_auth=need_auth)
        try:
            return requests.delete(f"{BASE_URL}{endpoint}", params=params, headers=headers)
        except Exception as e:
            st.error(f"Connection error to backend: {e}")
            return None
