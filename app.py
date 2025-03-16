from datetime import date
import base64
import os
import json
import pickle
import uuid
import re

import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")
st.title("MC Staff Movement")

# Sidebar Configuration
with st.sidebar:
    st.markdown("## Parameter Filters")
    start_date = st.date_input("Pick a start date", value=date.today())
    end_date = st.date_input("Pick an end date", value=date.today())

    access_token = st.text_input("Enter your access token here")

    def download_button(object_to_download, download_filename, button_text, pickle_it=False):
        """Generates a link to download the given object_to_download."""
        if pickle_it:
            try:
                object_to_download = pickle.dumps(object_to_download)
            except pickle.PicklingError as e:
                st.error(f"Error pickling object: {e}")
                return None
        else:
            if isinstance(object_to_download, bytes):
                pass
            elif isinstance(object_to_download, pd.DataFrame):
                object_to_download = object_to_download.to_csv(index=False).encode()
            else:
                object_to_download = json.dumps(object_to_download).encode()

        try:
            b64 = base64.b64encode(object_to_download).decode()
        except AttributeError as e:
            b64 = base64.b64encode(object_to_download).decode()

        button_uuid = str(uuid.uuid4()).replace('-', '')
        button_id = re.sub('\d+', '', button_uuid)

        custom_css = f"""
            <style>
                #{button_id} {{
                    background-color: rgb(255, 255, 255);
                    color: rgb(38, 39, 48);
                    padding: 0.25em 0.38em;
                    position: relative;
                    text-decoration: none;
                    border-radius: 4px;
                    border-width: 1px;
                    border-style: solid;
                    border-color: rgb(230, 234, 241);
                    border-image: initial;
                }}
                #{button_id}:hover {{
                    border-color: rgb(246, 51, 102);
                    color: rgb(246, 51, 102);
                }}
                #{button_id}:active {{
                    box-shadow: none;
                    background-color: rgb(246, 51, 102);
                    color: white;
                    }}
            </style> """

        dl_link = custom_css + f'<a download="{download_filename}" id="{button_id}" href="data:file/txt;base64,{b64}">{button_text}</a><br></br>'
        return dl_link

@st.cache_data(show_spinner=True)
def get_shifts(start_date, end_date, access_token):
    """Fetches shift data from the Humanity API."""
    if not access_token:
        st.warning("Please enter an access token in the sidebar.")
        return pd.DataFrame()

    try:
        url = f"https://www.humanity.com/api/v2/reports/custom?start_date={start_date}&end_date={end_date}&fields=id,employee,eid,location,schedule_name,start_day,end_day,start_time,end_time,&type=shifts&access_token={access_token}"
        response = requests.get(url)
        response.raise_for_status()
        custom_report = response.json()

        if "data" not in custom_report:
            st.error("Data not found in response. Check API token, start date, and end date")
            return pd.DataFrame()

        custom_report = custom_report["data"].values()
        custom_report = list(custom_report)[1:]

        if len(custom_report) > 0:
            custom_report = pd.Series(custom_report)
            custom_report = pd.DataFrame(custom_report)
            custom_report = custom_report[0].apply(pd.Series)
            custom_report['start_day'] = pd.to_datetime(custom_report['start_day'])
            custom_report['end_day'] = pd.to_datetime(custom_report['end_day'])

            # Initial sorting by employee and start_day
            custom_report = custom_report.sort_values(by=['employee', 'start_day'], ascending=True)

            def comp_prev(a):
                return np.concatenate(([False], a[1:] == a[:-1]))

            custom_report['prev_employee'] = comp_prev(custom_report.employee.values)
            custom_report['prev_location'] = comp_prev(custom_report.location.values)

            custom_report['prev_employee'] = custom_report['prev_employee'].astype(int)
            custom_report['prev_location'] = custom_report['prev_location'].astype(int)

            custom_report["Movement"] = np.where(
                (custom_report["prev_employee"] == 1) & (custom_report["prev_location"] == 0),
                "Movement",
                "No Movement"
            )

            del custom_report['prev_employee']
            del custom_report['prev_location']

            return custom_report
        else:
            return pd.DataFrame()

    except requests.exceptions.RequestException as e:
        st.error(f"API Request Error: {e}")
        return pd.DataFrame()
    except (KeyError, ValueError) as e:
        st.error(f"Error parsing API response: {e}")
        return pd.DataFrame()

# Main App Logic
if access_token:
    data = get_shifts(start_date, end_date, access_token)
else:
    st.warning("Please enter your access token to see the data.")
    data = pd.DataFrame()

if not data.empty:
    row_num = len(data)
    columns = ["Movement"]

    # Apply filters
    for column in data.columns:
        if column in columns:
            options = ["All"] + list(data[column].unique())
            choice = st.sidebar.selectbox(f"Select {column}:", options)
            if choice != "All":
                data = data[data[column] == choice]

    # After filters, sort by employee:
    data = data.sort_values(by=['employee'], ascending=True)

    st.subheader(f"The selected data has {row_num} rows of data, from {start_date} to {end_date}")
    st.dataframe(data)

    with st.sidebar:
        st.markdown(download_button(data, f"Staff_Schedules_{start_date}_to_{end_date}.csv", 'Download CSV', pickle_it=False), unsafe_allow_html=True)
else:
    st.info("No Data to display")
