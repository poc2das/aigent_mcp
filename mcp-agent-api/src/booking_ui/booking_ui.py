import streamlit as st
import requests

BACKEND_URL = "http://booking_agent:8002/bookMyFlight"
APPROVALS_URL = "http://booking_mcp_server:8008/pending_approvals"
APPROVE_TASK_URL = "http://booking_mcp_server:8008/approve"
RESULT_URL_BASE = "http://booking_mcp_server:8008/result"

def process_booking(prompt: str):
    try:
        response = requests.post(BACKEND_URL, json={"prompt": prompt})
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_pending_approvals():
    try:
        response = requests.get(APPROVALS_URL)
        return response.json()
    except Exception as e:
        return []

def approve_task(task_id, approved, edited_prompt=None):
    try:
        data = {"approved": str(approved).lower()}
        if edited_prompt is not None:
            data["edited_prompt"] = edited_prompt
        response = requests.post(f"{APPROVE_TASK_URL}/{task_id}", data=data)
        if response.status_code != 200:
            return {"error": f"Approval failed: {response.text}"}
        
        # Fetch booking result after approval
        result_response = requests.get(f"{RESULT_URL_BASE}/{task_id}")
        if result_response.status_code == 200:
            return result_response.json()
        else:
            return {"error": f"Failed to fetch booking result: {result_response.text}"}
    except Exception as e:
        return {"error": str(e)}

st.set_page_config(page_title="Natural Language Flight Booker", page_icon="✈️")
st.title("Natural Language Flight Booking 🛫")

menu = st.sidebar.selectbox("Menu", ["Book Flight", "Pending Approvals"])

if menu == "Book Flight":
    st.markdown("""
    Enter your flight booking request in natural language.  
    Example: _"Please book my flight ticket based on my availability, my name is Aswini"_
    """)
    user_prompt = st.text_area("Enter your booking request:", height=150)
    if st.button("Process Request"):
        if not user_prompt.strip():
            st.error("Please enter a booking request")
        else:
            with st.spinner("Processing your request..."):
                result = process_booking(user_prompt)
            if "error" in result:
                st.error(f"Error: {result['error']}")
                if "raw_response" in result:
                    st.text(f"Raw response: {result['raw_response']}")
            else:
                st.success("Booking Processed Successfully!")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.subheader("Calendar Check")
                    st.info(f"**Available Day:** {result.get('available_day', 'N/A')}")
                with col2:
                    st.subheader("Flight Found")
                    st.success(f"**{result.get('airline', 'N/A')}** at {result.get('timing', 'N/A')} ({result.get('date', 'N/A')})")
                with col3:
                    st.subheader("Confirmation")
                    st.success(f"**Status:** {result.get('booking_status', 'N/A')}")
                st.divider()
                st.json(result)

elif menu == "Pending Approvals":
    st.header("Pending Booking Approvals")
    tasks = get_pending_approvals()
    if not tasks:
        st.info("No pending approvals at the moment.")
    else:
        for task in tasks:
            st.markdown(f"### Task ID: {task['id']}")
            edited_prompt = st.text_area("Booking Details / Prompt", value=task["prompt"], key=task["id"])
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Approve {task['id']}"):
                    res = approve_task(task["id"], True, edited_prompt)
                    if "error" in res:
                        st.error(f"Error approving: {res['error']}")
                    else:
                        st.success(f"Task {task['id']} approved.")
                        st.json(res)  # Display booking confirmation and details
            with col2:
                if st.button(f"Reject {task['id']}"):
                    res = approve_task(task["id"], False)
                    if "error" in res:
                        st.error(f"Error rejecting: {res['error']}")
                    else:
                        st.warning(f"Task {task['id']} rejected.")
