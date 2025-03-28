from airflow import DAG
from datetime import datetime, timedelta
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.http.hooks.http import HttpHook
from airflow.operators.python import PythonOperator
import pandas as pd
import requests
import json
import pytz
import os
import boto3

from common import app_config


MALAYSIA_TZ = pytz.timezone('Asia/Kuala_Lumpur')

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 3, 20),
    'email': ['alvinwen3@gmail.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

def kelvin_to_celsius(temp_kelvin):
    return round(temp_kelvin - 273.15, 2)

def convert_unix_to_myt(unix_timestamp):
    utc_time = datetime.utcfromtimestamp(unix_timestamp).replace(tzinfo=pytz.utc)
    myt_time = utc_time.astimezone(MALAYSIA_TZ)
    return myt_time.strftime('%Y-%m-%d %H:%M:%S')


def transform_load_data(task_instance):
    """
    Transform and load weather data to a CSV file.
    - Extracts weather data from XCom
    - Converts to DataFrame
    - Saves to CSV
    - Uploads to S3
    """
    # Extract weather data from XCom
    weather_data = task_instance.xcom_pull(task_ids='extract_weather_data')

    snapshot_timestamp = datetime.utcfromtimestamp(weather_data["dt"]).strftime('%Y-%m-%d %H:%M:%S')

    temp_celsius = kelvin_to_celsius(weather_data["main"]["temp"])
    feels_like_celsius = kelvin_to_celsius(weather_data["main"]["feels_like"])
    temp_min_celsius = kelvin_to_celsius(weather_data["main"]["temp_min"])
    temp_max_celsius = kelvin_to_celsius(weather_data["main"]["temp_max"])

    place_name = weather_data.get("name", "Unknown")
    country = weather_data["sys"].get("country", "Unknown")

    sunrise_time = convert_unix_to_myt(weather_data["sys"]["sunrise"])
    sunset_time = convert_unix_to_myt(weather_data["sys"]["sunset"])

    # Convert to DataFrame
    df = pd.DataFrame({
        "Snapshot_data": [snapshot_timestamp],  
        "Place": [place_name],  
        "Country": [country],
        "Sunrise_time": [sunrise_time], 
        "Sunset_time": [sunset_time],  
        "temp_C": [temp_celsius],
        "feels_like_C": [feels_like_celsius],
        "temp_min_C": [temp_min_celsius],
        "temp_max_C": [temp_max_celsius],
        "pressure": [weather_data["main"]["pressure"]],
        "humidity": [weather_data["main"]["humidity"]],
        "wind_speed": [weather_data["wind"]["speed"]],
        "wind_deg": [weather_data["wind"]["deg"]],
        "clouds": [weather_data["clouds"]["all"]],
        "weather": [weather_data["weather"][0]["description"]],
    })

    """
    Get the AWS credentials acess key and secret key
    In the terminal install 'brew awscli' and run 'aws configure' to get the access key and secret key
    Type in aws sts get-session-token 

    If you have any issues, remove and try again
    rm -rf ~/.aws/credentials ~/.aws/config
    aws configure

    """

    now = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"{now}.csv" 
    local_filepath = f"/tmp/{filename}"  # Save locally first

    # Save DataFrame as CSV
    df.to_csv(local_filepath, index=False)

    AWS_ACCESS = app_config['aws_s3']['AWS_ACCESS_KEY_ID']
    AWS_SECRET = app_config['aws_s3']['AWS_SECRET_ACCESS_KEY']
    AWS_TOKEN = app_config['aws_s3']['AWS_TOKEN']

    # Upload to S3 using boto3
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS,
        aws_secret_access_key=AWS_SECRET,
        aws_session_token=AWS_TOKEN
    )

    bucket_name = "weather-s3bucket"
    s3_filepath = f"{country}/{filename}"

    try:
        s3_client.upload_file(local_filepath, bucket_name, s3_filepath)
        print(f"File successfully uploaded to S3: s3://{bucket_name}/{s3_filepath}")
    except Exception as e:
        print(f"Error uploading file to S3: {e}")
        raise (f"Error uploading file to S3: {e}")
        

def get_api_key():
    """Fetch API key from Airflow connection."""
    http_hook = HttpHook(method="GET", http_conn_id="weathermap_api")
    conn = http_hook.get_connection(http_hook.http_conn_id)
    return conn.extra_dejson.get("api_key")

API_KEY = get_api_key() 

"""
we save the API key in Airflow Connections.
Connection type is 'HTTP' and the host is 'api.openweathermap.org'.
The connection_id is 'weathermap_api' and the extra field is a JSON object with the API key.

{
  "api_key": "your_actual_api_key"
}
"""

def extract_weather_data():

    full_url = f"https://api.openweathermap.org/data/2.5/weather?lat=1.3521&lon=103.8198&appid={API_KEY}"
    
    response = requests.get(full_url)
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Headers: {response.headers}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        raise ValueError(f"API request failed: {response.status_code} {response.text}")

with DAG(
    'weather_dag',
    default_args=default_args,
    description='A simple weather DAG',
    schedule_interval=timedelta(days=1),
) as dag:
    
    is_weather_available = HttpSensor(
        task_id='is_weather_available',
        http_conn_id='weathermap_api',
        endpoint=f"data/2.5/weather?lat=1.3521&lon=103.8198&appid={API_KEY}",
        response_check=lambda response: response.status_code == 200
    )

    extract_weather = PythonOperator(
        task_id='extract_weather_data',
        python_callable=extract_weather_data,
    )

    transform_load_weather_data = PythonOperator(
        task_id='transform_load_weather_data',
        python_callable=transform_load_data
    )

    is_weather_available >> extract_weather >> transform_load_weather_data