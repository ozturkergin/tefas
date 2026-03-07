import streamlit as st
import subprocess
import os

def run_extract_script(tefas_price, calculate_indicators, tefas_fundtype, timedelta):
    # Construct the command with all required arguments
    command = [
        "python3",
        "page/extract.py",
        f"--tefas_price={'true' if tefas_price else 'false'}",
        f"--calculate_indicators={'true' if calculate_indicators else 'false'}",
        f"--tefas_fundtype={'true' if tefas_fundtype else 'false'}",
        f"--timedelta={timedelta}"
    ]

    try:
        # Run the script and capture output
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd="/app"
        )
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr
    except Exception as e:
        return "", f"Error running script: {str(e)}"

# Streamlit interface
st.title("Run Extract Script")
st.write("Configure arguments for page/extract.py")

# Form for arguments
with st.form("extract_form"):
    tefas_price = st.checkbox("Tefas Price (--tefas_price)", value=True)
    calculate_indicators = st.checkbox("Calculate Indicators (--calculate_indicators)", value=True)
    tefas_fundtype = st.checkbox("Tefas Fund Type (--tefas_fundtype)", value=False)
    timedelta = st.number_input("Timedelta (--timedelta, days)", min_value=1, value=30, step=1)
    submit_button = st.form_submit_button("Start")

    if submit_button:
        st.write("Running script with arguments...")
        st.write(f"Arguments: tefas_price={tefas_price}, calculate_indicators={calculate_indicators}, tefas_fundtype={tefas_fundtype}, timedelta={timedelta}")
        stdout, stderr = run_extract_script(tefas_price, calculate_indicators, tefas_fundtype, timedelta)
        
        if stdout:
            st.success("Script Output:")
            st.code(stdout, language="text")
        if stderr:
            st.error("Script Errors:")
            st.code(stderr, language="text")
    
        st.cache_data.clear()
        st.session_state.clear()