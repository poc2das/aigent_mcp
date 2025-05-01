import streamlit as st
import requests

BACKEND_URL = "http://booking_agent:8002/bookMyFlight"

def process_booking(prompt: str):
    try:
        response = requests.post(BACKEND_URL, json={"prompt": prompt})
        return response.json()
    except Exception as e:
        return {"error": str(e)}

st.set_page_config(page_title="Natural Language Flight Booker", page_icon="✈️")
st.title("Natural Language Flight Booking 🛫")

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
            st.json(result)  # Show full response for transparency
