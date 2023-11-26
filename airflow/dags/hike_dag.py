import datetime
import urllib.request as request
import pandas as pd
import requests
import random
import json

from helpers import extract_hikes_data, transformation_redis_hikes,insert_mongo,insert_data_mongo_in_neo4j, call_reddit_api, natural_language_processing, add_topics_neo4j, check_internet_connection, extract_hikes_data_offline

import airflow
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.postgres_operator import PostgresOperator


# Increase for production
REDDIT_API_POST_LIMIT = 2

default_args_dict = {
    'start_date': airflow.utils.dates.days_ago(0),
    'concurrency': 1,
    'schedule_interval': None,
    'retries': 0,
    'retry_delay': datetime.timedelta(minutes=5),
}

dag = airflow.DAG(
    dag_id='hike_dag',
    default_args=default_args_dict,
    catchup=False,
    template_searchpath=['/opt/airflow/dags/']
)


# Nodes

start = DummyOperator(
    task_id='start', 
    dag=dag,
    trigger_rule='all_success',
)

check_connection_hikes_data = BranchPythonOperator(
    task_id='check_connection_hikes_data',
    python_callable=check_internet_connection,
    op_kwargs={
        "online_task": "extract_hikes_online",
        "offline_task": "extract_hikes_offline",
    },
    dag=dag,
    depends_on_past=False,
    trigger_rule='all_success',
)

extract_hikes_offline = PythonOperator(
    task_id='extract_hikes_offline',
    python_callable=extract_hikes_data_offline,
    op_kwargs={
        "url": "https://besthikesbc.ca/hike-database/"
    },
    dag=dag,
    depends_on_past=False,
    trigger_rule='all_success',
)
    
extract_hikes_online = PythonOperator(
    task_id='extract_hikes_online',
    python_callable=extract_hikes_data,
    op_kwargs={
        "url": "https://besthikesbc.ca/hike-database/"
    },
    dag=dag,
    depends_on_past=False,
    trigger_rule='all_success',
)

transform_hikes = PythonOperator(
    task_id='transform_hikes_data',
    python_callable=transformation_redis_hikes,
    op_kwargs={
        "hike_key": "extract_hiking"
    },
    dag=dag,
    depends_on_past=False,
    trigger_rule='none_failed',
)

add_hikes_to_mongo = PythonOperator(
    task_id = "add_hikes_to_mongo",
    dag = dag,
    python_callable = insert_mongo,
    depends_on_past=False,
    trigger_rule='none_failed',
)

insert_data_mongo_in_graph = PythonOperator(
    task_id = "extract_data_hikes_to_mongo",
    dag = dag,
    python_callable = insert_data_mongo_in_neo4j,
    depends_on_past=False,
    trigger_rule='none_failed',
)

### Legacy: Dags for Postgres

    # generate_script_hikes = PythonOperator(
    #     task_id='generate_insert',
    #     dag=dag,
    #     python_callable=_insert,
    #     trigger_rule='none_failed',
    # )

    # load_hikes = PostgresOperator(
    #     task_id='insert_inserts',
    #     dag=dag,
    #     postgres_conn_id='postgres_default',
    #     sql='inserts.sql',
    #     trigger_rule='none_failed',
    #     autocommit=True
    # )

# Task to call Reddit API for each hike_name
call_reddit_api_node = PythonOperator(
    task_id='call_reddit_api',
    dag=dag,
    python_callable=call_reddit_api,
    op_kwargs={
        "limit": REDDIT_API_POST_LIMIT,
        "subreddit_name": "hiking"
    },
    depends_on_past=False,
    trigger_rule='none_failed',
)

perform_natural_language_processing= PythonOperator(
    task_id='perform_natural_language_processing',
    dag=dag,
    python_callable=natural_language_processing,
    depends_on_past=False,
    trigger_rule='none_failed',
)

add_topics_graph = PythonOperator(
    task_id='add_topics_graph',
    dag=dag,
    python_callable=add_topics_neo4j,
    depends_on_past=False,
    trigger_rule='none_failed',
)

end = DummyOperator(
    task_id='end', 
    dag=dag,
    trigger_rule='all_done',
)


start >> check_connection_hikes_data >> [extract_hikes_online, extract_hikes_offline] >> transform_hikes 
transform_hikes >> add_hikes_to_mongo >> call_reddit_api_node >> perform_natural_language_processing >> insert_data_mongo_in_graph >> add_topics_graph >> end