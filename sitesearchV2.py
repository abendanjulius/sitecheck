import pandas as pd
import streamlit as st
import time
import json
import os
import datetime
from googleapiclient.discovery import build
from urllib.parse import urlparse
import plotly.express as px
import requests
from PIL import Image
from io import BytesIO


# Function to load the profile picture
def load_profile_picture():
    image_url = "https://media.licdn.com/dms/image/v2/D4E03AQEA53bIRNPJYg/profile-displayphoto-shrink_200_200/B4EZTzV0CGGwAY-/0/1739249370304?e=2147483647&v=beta&t=5l0b-khsQiMrS6En7woYUS1HzHAurbfnXEWTzsjdUw8"
    try:
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        return img
    except Exception as e:
        st.sidebar.error(f"Error loading profile image: {str(e)}")
        return None


# Function to check the usage file
def check_usage_file():
    usage_file = "api_usage.json"
    if os.path.exists(usage_file):
        try:
            with open(usage_file, "r") as f:
                usage_data = json.load(f)
                st.sidebar.success("Usage file found!")
                st.sidebar.json(usage_data)
                return usage_data
        except Exception as e:
            st.sidebar.error(f"Error reading usage file: {str(e)}")
            return {"date": datetime.datetime.now().strftime("%Y-%m-%d"), "count": 0}
    else:
        st.sidebar.warning(f"Usage file not found at: {os.path.abspath(usage_file)}")
        st.sidebar.info("A new file will be created.")
        return {"date": datetime.datetime.now().strftime("%Y-%m-%d"), "count": 0}


# Function to load or initialize the usage stats
def load_usage_stats():
    usage_file = "api_usage.json"
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    if os.path.exists(usage_file):
        try:
            with open(usage_file, "r") as f:
                usage_data = json.load(f)

            # Check if we have data for today
            if usage_data.get("date") != today:
                # Reset for new day
                usage_data = {"date": today, "count": 0}
        except:
            usage_data = {"date": today, "count": 0}
    else:
        usage_data = {"date": today, "count": 0}

    return usage_data


# Function to save usage stats
def save_usage_stats(usage_data):
    usage_file = "api_usage.json"
    with open(usage_file, "w") as f:
        json.dump(usage_data, f)


def check_google_index(url, api_key, search_engine_id):
    try:
        # Use the exact URL for searching
        clean_url = url.strip()

        # Build the service with API key
        service = build("customsearch", "v1", developerKey=api_key)

        # Execute the search for the exact URL
        result = service.cse().list(
            q=f"\"{clean_url}\"",  # Use quotes for exact match
            cx=search_engine_id
        ).execute()

        # Check if there are any search results
        if "items" in result and len(result["items"]) > 0:
            # Get the first result URL exactly as it appears
            first_url = result["items"][0]["link"]
            return "indexed", first_url
        else:
            # Only report if the exact URL is indexed or not
            return "not indexed", ""

    except Exception as e:
        st.error(f"Error checking {url}: {str(e)}")
        return "error", str(e)


def process_urls(df, api_key, search_engine_id, usage_data):
    # Add a progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Find the URL column (assume it's the first column if not specified)
    url_column = df.columns[0]
    st.info(f"Using URL column: {url_column}")

    # Add columns for indexing status and indexed URL if they don't exist
    if "Indexed Status" not in df.columns:
        df["Indexed Status"] = ""
    if "Indexed URL" not in df.columns:
        df["Indexed URL"] = ""

    # Initialize counters
    indexed_count = 0
    not_indexed_count = 0
    error_count = 0

    # Process each URL
    for index, row in df.iterrows():
        url = str(row[url_column])
        if pd.isna(url) or url == "":
            continue

        # Check if we've hit the daily limit
        if usage_data["count"] >= 100:
            st.warning("Daily API quota of 100 requests has been reached!")
            break

        # Update status
        progress = (index + 1) / len(df)
        progress_bar.progress(progress)
        status_text.text(f"Checking ({index + 1}/{len(df)}): {url}")

        # Check if URL is indexed - using exact URL match
        indexing_status, indexed_url = check_google_index(url, api_key, search_engine_id)

        # Update the DataFrame
        df.at[index, "Indexed Status"] = indexing_status
        df.at[index, "Indexed URL"] = indexed_url

        # Update counters
        if indexing_status == "indexed":
            indexed_count += 1
        elif indexing_status == "not indexed":
            not_indexed_count += 1
        else:
            error_count += 1

        # Update usage count
        usage_data["count"] += 1
        save_usage_stats(usage_data)

        # Add a small delay to avoid hitting API rate limits
        time.sleep(0.5)

    progress_bar.progress(1.0)
    status_text.text("All URLs have been processed!")

    return df, indexed_count, not_indexed_count, error_count


# Hardcoded values
API_KEY = "AIzaSyBWq9DsenwWQlB6zsNhK151ygfYHRUY_L8"
SEARCH_ENGINE_ID = "8249476f72f974a92"

# Streamlit UI
st.set_page_config(page_title="Google Index Checker", layout="wide")

# Sidebar with app title
with st.sidebar:
    st.title("Google Index Checker")

    # Load and display profile picture
    profile_pic = load_profile_picture()
    if profile_pic:
        st.image(profile_pic, width=150)
    else:
        try:
            st.image("logo.png", width=250)
        except:
            st.write("GO GLE Indexing Tool")

    # Automatic file check
    st.subheader("Usage File Status")
    current_usage = check_usage_file()

    # Load usage stats
    usage_data = load_usage_stats()
    remaining_quota = 100 - usage_data["count"]

    # API quota information
    st.subheader("API Usage Today")
    st.metric("Remaining API Calls", f"{remaining_quota}/100")
    st.progress(usage_data["count"] / 100)
    st.caption(f"Resets at midnight (Current date: {usage_data['date']})")

    # Add a button to reset the counter if needed
    if st.button("Reset Counter"):
        usage_data["count"] = 0
        save_usage_stats(usage_data)
        st.success("Counter reset successfully!")
        st.rerun()

    # Only need Search Engine ID input now
    st.subheader("API Credentials")
    st.success("API Key: Already configured ✓")
    st.success(f"Search Engine ID: {SEARCH_ENGINE_ID} ✓")

# Main app area
st.title("Google Index Checker")
st.write("Upload a CSV file with URLs to check if they are indexed on Google.")

# Only enable file upload if quota isn't exhausted
if remaining_quota > 0:
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
else:
    st.error("Daily API quota exhausted. Please try again tomorrow or reset the counter.")
    uploaded_file = None

if uploaded_file is not None:
    # Read the CSV file
    df = pd.read_csv(uploaded_file)
    st.write(f"Loaded {len(df)} URLs from the file")

    # Show a preview of the data
    st.subheader("Preview of uploaded data")
    st.dataframe(df.head())

    # Add a single button to start processing (only if quota available)
    if remaining_quota > 0 and st.button("Check URLs"):
        try:
            with st.spinner('Processing URLs...'):
                result_df, indexed_count, not_indexed_count, error_count = process_urls(df, API_KEY, SEARCH_ENGINE_ID,
                                                                                        usage_data)

            # Display the results
            st.subheader("Results")
            st.dataframe(result_df)

            # Create and display pie chart
            col1, col2 = st.columns([1, 1])

            with col1:
                st.subheader("Indexation Summary")
                # Create pie chart data
                pie_data = pd.DataFrame({
                    'Status': ['Indexed', 'Not Indexed', 'Error'],
                    'Count': [indexed_count, not_indexed_count, error_count]
                })

                # Filter out zero values
                pie_data = pie_data[pie_data['Count'] > 0]

                if not pie_data.empty:
                    fig = px.pie(
                        pie_data,
                        values='Count',
                        names='Status',
                        color='Status',
                        color_discrete_map={
                            'Indexed': 'green',
                            'Not Indexed': 'red',
                            'Error': 'gray'
                        },
                        title=f"Indexation Status ({indexed_count + not_indexed_count + error_count} URLs)"
                    )
                    st.plotly_chart(fig)
                else:
                    st.info("No data available for chart")

            with col2:
                st.subheader("API Usage")
                st.write(f"API calls used in this session: {indexed_count + not_indexed_count + error_count}")
                st.write(f"Remaining API calls today: {100 - usage_data['count']}")
                st.progress((100 - usage_data["count"]) / 100)

            # Provide a download button for the results
            csv = result_df.to_csv(index=False)
            st.download_button(
                label="Download results as CSV",
                data=csv,
                file_name="google_index_results.csv",
                mime="text/csv"
            )

            # Removed the rerun after processing to avoid empty results

        except Exception as e:
            st.error(f"Error initializing the Google API: {str(e)}")