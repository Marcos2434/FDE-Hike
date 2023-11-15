import datetime
import urllib.request as request
import pandas as pd
import requests
import random
import json

from helpers import call_reddit_api, natural_language_processing

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



call_reddit_api_node = PythonOperator(
    task_id='call_reddit_api',
    dag=dag,
    python_callable=call_reddit_api,
    op_kwargs={
        "hike_name": "Half Dome",
        "limit": 2,
        "subreddit_name": "hiking"
    },
    depends_on_past=False
)

perform_natural_language_processing= PythonOperator(
    task_id='perform_natural_language_processing',
    dag=dag,
    python_callable=natural_language_processing,
    depends_on_past=False
)

end = DummyOperator(
    task_id='end', 
    dag=dag
)

start >> call_reddit_api_node >> perform_natural_language_processing >> end