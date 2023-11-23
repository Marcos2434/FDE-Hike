import datetime
import urllib.request as request
import pandas as pd
import requests
import random
import json

from helpers import extract_hikes_data, transformation_redis_hikings,insert_mongo,insert_data_mongo_in_neo4j, call_reddit_api, natural_language_processing,nature_neo4j

import airflow
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.postgres_operator import PostgresOperator


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
    dag=dag
)

extract_hikings = PythonOperator(
    task_id='extract_hikes_data',
    python_callable=extract_hikes_data,
    op_kwargs={
        "url": "https://besthikesbc.ca/hike-database/"
    },
    dag=dag,
    depends_on_past=False
)

transform_hikings = PythonOperator(
    task_id='transform_hikes_data',
    python_callable=transformation_redis_hikings,
    op_kwargs={
        "hike_key": "extract_hiking"
    },
    dag=dag,
    depends_on_past=False
)

add_hikings_to_mongo = PythonOperator(
    task_id = "add_hikings_to_mongo",
    dag = dag,
    python_callable = insert_mongo,
    op_kwargs={
        "hike_key": "extract_hiking"
    },
    depends_on_past=False
)

insert_data_mongo_in_graph = PythonOperator(
    task_id = "extract_data_hikings_to_mongo",
    dag = dag,
    python_callable = insert_data_mongo_in_neo4j,
    depends_on_past=False
)

### Dags for Postgres

    # generate_script_hikings = PythonOperator(
    #     task_id='generate_insert',
    #     dag=dag,
    #     python_callable=_insert,
    #     trigger_rule='none_failed',
    # )

    # load_hikings = PostgresOperator(
    #     task_id='insert_inserts',
    #     dag=dag,
    #     postgres_conn_id='postgres_default',
    #     sql='inserts.sql',
    #     trigger_rule='all_success',
    #     autocommit=True
    # )

# Task to call Reddit API for each hike_name
call_reddit_api_node = PythonOperator(
    task_id='call_reddit_api',
    dag=dag,
    python_callable=call_reddit_api,
    op_kwargs={
        "limit": 2,
        "subreddit_name": "hiking"
    },
    depends_on_past=False
)

# call_reddit_api_node = PythonOperator(
#     task_id='call_reddit_api',
#     dag=dag,
#     python_callable=call_reddit_api,
#     op_kwargs={
#         "hike_name": "Teapot Hill",
#         "limit": 2,
#         "subreddit_name": "hiking"
#     },
#     depends_on_past=False
# )


perform_natural_language_processing= PythonOperator(
    task_id='perform_natural_language_processing',
    dag=dag,
    python_callable=natural_language_processing,
    depends_on_past=False
)

add_nature_hike = PythonOperator(
    task_id='add_nature_hike',
    dag=dag,
    python_callable=nature_neo4j,
    op_kwargs={
        "hike_name": "Teapot Hill"
    },
    depends_on_past=False
)

end = DummyOperator(
    task_id='end', 
    dag=dag
)


start >> extract_hikings >> transform_hikings >> add_hikings_to_mongo >> insert_data_mongo_in_graph >> call_reddit_api_node >> perform_natural_language_processing >> add_nature_hike >> end