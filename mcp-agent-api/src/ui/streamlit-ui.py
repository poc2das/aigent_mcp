import streamlit as st
import requests

st.title("Simple Math Prompt UI")

st.header("Submit Math Prompt")

prompt = st.text_area("Enter your math prompt (e.g., 'Add 5 and 7')")

if st.button("Submit"):
    if not prompt.strip():
        st.warning("Please enter a valid prompt.")
    else:
        with st.spinner("Processing..."):
            try:
                response = requests.post(
                    "http://fastapi_agent:8002/analyze",  # Adjust hostname/port if needed
                    json={"prompt": prompt}
                )
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data:
                        st.success(f"Result: {data['result']}")
                    elif "error" in data:
                        st.error(f"Error: {data['error']}")
                    else:
                        st.info(f"Response: {data}")
                else:
                    st.error(f"Error from server: {response.text}")
            except Exception as e:
                st.error(f"Request failed: {str(e)}")
