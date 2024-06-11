from airflow import DAG
from datetime import timedelta,datetime,timezone
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.http.operators.http import SimpleHttpOperator
import json
from airflow.operators.python import PythonOperator
import pandas as pd
import boto3
import pandas as pd

def kelvin_to_fahrenheit(temp_in_kelvin):
    temp_in_fahrenheit = (temp_in_kelvin - 273.15) * (9/5) + 32
    return temp_in_fahrenheit


def transform_load_data(task_instance):
    data = task_instance.xcom_pull(task_ids="extract_weather_data")
    city = data["name"]
    weather_description = data["weather"][0]['description']
    temp_farenheit = kelvin_to_fahrenheit(data["main"]["temp"])
    feels_like_farenheit= kelvin_to_fahrenheit(data["main"]["feels_like"])
    min_temp_farenheit = kelvin_to_fahrenheit(data["main"]["temp_min"])
    max_temp_farenheit = kelvin_to_fahrenheit(data["main"]["temp_max"])
    pressure = data["main"]["pressure"]
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]
    time_of_record = datetime.fromtimestamp(data['dt'], timezone.utc) + timedelta(seconds=data['timezone'])
    sunrise_time = datetime.fromtimestamp(data['sys']['sunrise'], timezone.utc) + timedelta(seconds=data['timezone'])
    sunset_time = datetime.fromtimestamp(data['sys']['sunset'], timezone.utc) + timedelta(seconds=data['timezone'])
    
    transformed_data = {"City": city,
                        "Description": weather_description,
                        "Temperature (F)": temp_farenheit,
                        "Feels Like (F)": feels_like_farenheit,
                        "Minimun Temp (F)":min_temp_farenheit,
                        "Maximum Temp (F)": max_temp_farenheit,
                        "Pressure": pressure,
                        "Humidty": humidity,
                        "Wind Speed": wind_speed,
                        "Time of Record": time_of_record,
                        "Sunrise (Local Time)":sunrise_time,
                        "Sunset (Local Time)": sunset_time                        
                        }
    transformed_data_list = [transformed_data]
    df_data = pd.DataFrame(transformed_data_list)


    now = datetime.now()
    dt_string = now.strftime("%d%m%Y%H%M%S")
    dt_string = 'current_weather_data_portland_' + dt_string
    # df_data.to_csv("data2.csv",index=False)
    df_data.to_csv('data1.csv',index=False)


    session = boto3.Session(
   region_name='',
    aws_access_key_id='',
    aws_secret_access_key=''
        )

    s3_upload = session.client('s3')
    s3_upload.upload_file('data1.csv', 'dataweather','data1.csv')
    

default_args={
    'owner':'vinayak',
    'depends_on_past':False,
    'start_date':datetime(2024,6,11),
    'email':'vinyakkumar808@gmail.com',
'email_on_failiure':True,
    'retries':2
}
with DAG(
    'Weather_api',
    default_args=default_args,
    description='A  DAG for my first project',
    
    tags=['api'],
    catchup=False
) as dag:
    
    is_api_ready=HttpSensor(
        task_id='is_api_ready',
        http_conn_id='First_ETL_Pipeline',
        endpoint='/data/2.5/weather?q=Portland&APPID='
    )
    extract_data= SimpleHttpOperator(
        task_id="extract_weather_data",
        http_conn_id="First_ETL_Pipeline",
        method='GET',
        endpoint='/data/2.5/weather?q=Portland&APPID=',
        headers={"Content-Type": "application/json"},
        response_filter=lambda response: json.loads(response.text),
        log_response=True,
    )
    transform_data= PythonOperator(
        task_id="transform_data",
          python_callable=transform_load_data,
    provide_context=True
        
    )

is_api_ready>>extract_data>>transform_data
   


