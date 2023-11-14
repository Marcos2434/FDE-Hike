import airflow
import datetime
import urllib.request as request
import pandas as pd
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.postgres_operator import PostgresOperator

import requests
import random
from airflow.models import Variable
import json

# default_args_dict = {
#     'start_date': datetime.datetime(2023, 10, 5, 0, 0, 0), # The process should happen once a week, before friday evening's sessions -> So every thursday night at midnight
#     'concurrency': 1,
#     'schedule_interval': "0 0 * * 0", # run every week
#     'retries': 1,
#     'retry_delay': datetime.timedelta(minutes=5),
# }

default_args_dict = {
    'start_date': airflow.utils.dates.days_ago(0),
    'concurrency': 1,
    'schedule_interval': None,
    'retries': 0,
    'retry_delay': datetime.timedelta(minutes=5),
}

dnd_dag = DAG(
    dag_id='dnd_dag',
    default_args=default_args_dict,
    catchup=False,
    template_searchpath=['/opt/airflow/dags/']
)


def generate_character():
    fake = Faker()
    
    def new_character():
        return fake.first_name()
    
    # "attributes": {
    #     "strength": random.randint(6, 18), 
    #     "dexterity": random.randint(2, 18), 
    #     "constitution": random.randint(2, 18), 
    #     "intelligence": random.randint(2, 18), 
    #     "wisdom": random.randint(2, 18), 
    #     "charisma": random.randint(2, 18)
    #     },
    

    with open('/opt/airflow/dags/insert_characters.sql', 'w') as f:
        f.write(f"""
            CREATE TABLE IF NOT EXISTS characters (
                name VARCHAR(255)
            );
            INSERT INTO characters (name) VALUES ('{new_character()}');
        """)
        # json.dump(data, f)
        




def should_generate_characters():
    # Check if characters for the week already exist in the database
    # Return a task_id to continue or skip character generation
    
    
    
    # if characters_exist():
    if 1==2:
        return 'end'
    else:
        return 'generate_characters'


# start = DummyOperator(
#     task_id='start', 
#     dag=dnd_dag
# )

# generate_characters_task = PythonOperator(
#     task_id='generate_characters',
#     python_callable=generate_character,
#     provide_context=True,  # Pass context to the Python function
#     dag=dnd_dag,
# )


# # branch_task = BranchPythonOperator(
# #     task_id='check_character_generation',
# #     python_callable=should_generate_characters,
# #     provide_context=True,  # Pass context to the Python function
# #     dag=dnd_dag,
# # )

# insert_characters_task = PostgresOperator(
#     task_id='insert_characters',
#     postgres_conn_id='postgres_default',
#     sql='./insert_characters.sql',  # SQL script to insert characters into the database
#     parameters={
#         'name': 'Wizard-1',
#         'attributes': '[16, 12, 10, 6, 10, 14]'
#     },
#     dag=dnd_dag,
# )


# end = DummyOperator(
#     task_id='end',
#     dag=dnd_dag,
#     trigger_rule='none_failed'
# )


start = DummyOperator(
    task_id='start', 
    dag=dnd_dag
)

fetch_character_data = PythonOperator(
    task_id='fetch_character_data',
    dag=dnd_dag,
    python_callable=generate_character,
    provide_context=True # Pass context to the Python function OTHERWISE you get an error
)


# test_get_data = PythonOperator(
#     task_id='test_get_data',
#     dag=dnd_dag,
#     python_callable=lambda: print(fetch_character_data.xcom_pull(task_ids='test_get_data', key='characters'))
# )

insert_character_postrgres  = PostgresOperator(
    task_id='insert_data',
    sql="insert_characters.sql",
    # parameters="",
    postgres_conn_id='postgres_default',  # Specify the PostgreSQL connection ID
    autocommit=True,  # Setting autocommit to True if the query doesn't require a transaction
    dag=dnd_dag,
)

end = DummyOperator(
    task_id='end',
    dag=dnd_dag,
    trigger_rule='none_failed'
)


start >> fetch_character_data >> insert_character_postrgres >> end
# start >> fetch_character_data >> test_get_data >> end
# start >> fetch_character_data >> end