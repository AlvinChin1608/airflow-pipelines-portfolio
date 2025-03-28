# Airflow Weather Data Pipeline

This project is an Apache Airflow DAG that automates the extraction, transformation, and storage of weather data from the OpenWeatherMap API. The data is processed and uploaded to an AWS S3 bucket for further analysis.

## Features
- Extracts real-time weather data from OpenWeatherMap API.
- Converts temperature from Kelvin to Celsius.
- Converts UNIX timestamps to Local Time (MYT).
- Saves processed data as a CSV file.
- Uploads the CSV file to an AWS S3 bucket.
- Uses Airflow sensors and operators to manage workflow execution.

## Getting Started
### Prerequisites
Ensure you have the following installed:
- Docker
- Docker Compose
- AWS CLI
- Python 3.12
- Apache Airflow

## Setting Up AWS Credentials
After obtaining your AWS Security Access Credentials, configure AWS credentials for S3 access:

```python
brew install awscli  # (For macOS, install AWS CLI)
aws configure  # Set up AWS credentials
aws sts get-session-token  # This should give you the access key, secret and token
```

If you face any issues, reset your AWS credentials:

```python
rm -rf ~/.aws/credentials ~/.aws/config
aws configure
```

## Running the Project with Docker
To start Airflow and related services using Docker:

```python
docker-compose up -d
```

To stop the services:

```python
docker-compose down
```

In your browser, go to localhost:8080 or http://0.0.0.0:8080, then log in with the username and password: airflow.

## Airflow Setup 
1. Add an Airflow connection for OpenWeatherMap API:
![](https://github.com/AlvinChin1608/airflow-pipelines-portfolio/blob/main/demo/airflowconnection.png)

- Connection Type: HTTP
- Host: api.openweathermap.org
- Connection ID: weathermap_api
- Extra:
  ```python
  {
  "api_key": "1234"
  }
  ```

2. Start the DAG via the Airflow web UI







