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
import json
import glob
import pandas as pd

default_args_dict = {
    'start_date': datetime.datetime(2020, 6, 25, 0, 0, 0),
    'concurrency': 1,
    'schedule_interval': "0 0 * * *",
    'retries': 1,
    'retry_delay': datetime.timedelta(minutes=5),
}

assignment_dag = DAG(
    dag_id='assignment_dag',
    default_args=default_args_dict,
    catchup=False,
    template_searchpath=['/opt/airflow/data/']
)


# Downloading a file from an API/endpoint?

def _name_race(output_folder: str, endpoint: str, url: str):
    from faker import Faker
    fake = Faker()
    races_unfiltered = requests.get(f"{url}/{endpoint}").json()
    races = random.sample([i.get('index') for i in races_unfiltered.get('results')], 5)
    rand_names = [fake.first_name() for i in range(5)]
    final_dict = {"race": races,
                  "name": rand_names}
    with open(f'{output_folder}/first_node.json', 'w') as f:
        json.dump(final_dict, f, ensure_ascii=False)


first_node = PythonOperator(
    task_id='name_race',
    dag=assignment_dag,
    trigger_rule='none_failed',
    python_callable=_name_race,
    op_kwargs={
        "output_folder": "/opt/airflow/data",
        "endpoint": "races",
        "url": "https://www.dnd5eapi.co/api"
    },
    depends_on_past=False,
)


def _attributes(output_folder: str):
    attributes = [list(random.randint(6, 19) for i in range(5)) for j in range(5)]
    final_dict = {"attributes": attributes}
    with open(f'{output_folder}/second_node.json', 'w') as f:
        json.dump(final_dict, f, ensure_ascii=False)


second_node = PythonOperator(
    task_id='attributes',
    dag=assignment_dag,
    trigger_rule='none_failed',
    python_callable=_attributes,
    op_kwargs={
        "output_folder": "/opt/airflow/data",
    },
    depends_on_past=False,
)


def _language(output_folder: str, endpoint: str, url: str):
    languages_unfiltered = requests.get(f"{url}/{endpoint}").json()
    languages = random.sample([i.get('index') for i in languages_unfiltered.get('results')], 5)
    final_dict = {"language": languages}
    with open(f'{output_folder}/third_node.json', 'w') as f:
        json.dump(final_dict, f, ensure_ascii=False)


third_node = PythonOperator(
    task_id='language',
    dag=assignment_dag,
    trigger_rule='none_failed',
    python_callable=_language,
    op_kwargs={
        "output_folder": "/opt/airflow/data",
        "endpoint": "languages",
        "url": "https://www.dnd5eapi.co/api"
    },
    depends_on_past=False,
)


def _class(output_folder: str, endpoint: str, url: str):
    classes_unfiltered = requests.get(f"{url}/{endpoint}").json()
    classes = random.sample([i.get('index') for i in classes_unfiltered.get('results')], 5)
    final_dict = {"class": classes}
    with open(f'{output_folder}/fourth_node.json', 'w') as f:
        json.dump(final_dict, f, ensure_ascii=False)


fourth_node = PythonOperator(
    task_id='class',
    dag=assignment_dag,
    trigger_rule='none_failed',
    python_callable=_class,
    op_kwargs={
        "output_folder": "/opt/airflow/data",
        "endpoint": "classes",
        "url": "https://www.dnd5eapi.co/api"
    },
    depends_on_past=False,
)


def _proficiency_choices(output_folder: str, url: str):
    with open(f"{output_folder}/fourth_node.json", "r") as read_file:
        load_classes = json.load(read_file)

    classes = load_classes.get('class')

    def get_proficiences(classs):
        proficiences_unfiltered = requests.get(f"{url}/classes/{classs}").json()
        proficiency_choices = proficiences_unfiltered.get('proficiency_choices')[0]
        proficiency_options = proficiency_choices.get('from')
        choices = proficiency_choices.get('choose')
        proficiences = random.sample([i.get('index') for i in proficiency_options], choices)
        return proficiences

    final_dict = [get_proficiences(i) for i in classes]

    with open(f'{output_folder}/fifth_node.json', 'w') as f:
        json.dump({"proficiences": final_dict}, f, ensure_ascii=False)


fifth_node = PythonOperator(
    task_id='proficiency_choices',
    dag=assignment_dag,
    trigger_rule='none_failed',
    python_callable=_proficiency_choices,
    op_kwargs={
        "output_folder": "/opt/airflow/data",
        "url": "https://www.dnd5eapi.co/api"
    },
    depends_on_past=False,
)


def _levels(output_folder: str):
    random_levels = [random.randint(1, 3) for i in range(5)]
    with open(f'{output_folder}/sixth_node.json', 'w') as f:
        json.dump({"levels": random_levels}, f, ensure_ascii=False)


sixth_node = PythonOperator(
    task_id='levels',
    dag=assignment_dag,
    trigger_rule='none_failed',
    python_callable=_levels,
    op_kwargs={
        "output_folder": "/opt/airflow/data"
    },
    depends_on_past=False,
)


def _spell_check(output_folder, url):
    with open(f"{output_folder}/fourth_node.json", "r") as read_file:
        load_classes = json.load(read_file)

    classes = load_classes.get('class')

    def spellcount(classs):
        return requests.get(f"{url}/classes/{classs}/spells").json().get("count")

    spell_counts = [spellcount(i) for i in classes]

    if sum(spell_counts) > 0:
        return 'spells'
    else:
        return 'merge'


seventh_node = BranchPythonOperator(
    task_id='spell_check',
    dag=assignment_dag,
    python_callable=_spell_check,
    op_kwargs={
        "output_folder": "/opt/airflow/data",
        "url": "https://www.dnd5eapi.co/api"
    },
    trigger_rule='all_success',
)


def _spells(output_folder, url):
    with open(f"{output_folder}/fourth_node.json", "r") as read_file:
        load_classes = json.load(read_file)

    classes = load_classes.get('class')

    url = "https://www.dnd5eapi.co/api/"

    def get_spells(classs):
        spells_unfiltered = requests.get(f"{url}/classes/{classs}/spells").json()
        spell_count = spells_unfiltered.get('count')

        if spell_count > 0:
            spells_filtered = spells_unfiltered.get('results')
            spells = random.sample([i.get('index') for i in spells_filtered], random.randint(1, 3))
            return spells
        else:
            spells = "none"
            return spells

    spell_lists = [get_spells(i) for i in classes]

    with open(f'{output_folder}/seventh_node.json', 'w') as f:
        json.dump({"spells": spell_lists}, f, ensure_ascii=False)


seventh_node_a = PythonOperator(
    task_id='spells',
    dag=assignment_dag,
    python_callable=_spells,
    op_kwargs={
        "output_folder": "/opt/airflow/data",
        "url": "https://www.dnd5eapi.co/api"
    },
    trigger_rule='all_success',
)


def _merge(output_folder):
    jsons = glob.glob(f'{output_folder}/*.json')
    dfs = pd.concat(map(pd.read_json, jsons), 1)
    dfs.to_csv(path_or_buf=f'{output_folder}/eight_node.csv')


eight_node = PythonOperator(
    task_id='merge',
    dag=assignment_dag,
    python_callable=_merge,
    op_kwargs={
        "output_folder": "/opt/airflow/data"
    },
    trigger_rule='all_success',
)


def _insert(output_folder):
    df = pd.read_csv(f'{output_folder}/eight_node.csv')
    with open("/opt/airflow/data/inserts.sql", "w") as f:
        df_iterable = df.iterrows()
        f.write(
            "CREATE TABLE IF NOT EXISTS characters (\n"
            "race VARCHAR(255),\n"
            "name VARCHAR(255),\n"
            "proficiences VARCHAR(255),\n"
            "language VARCHAR(255),\n"
            "spells VARCHAR(255),\n"
            "classs VARCHAR(255),\n"
            "levels VARCHAR(255),\n"
            "attributes VARCHAR(255));\n"
        )
        for index, row in df_iterable:
            race = row['race']
            name = row['name']
            proficiences = row['proficiences']
            language = row['language']
            spells = row['spells']
            classs = row['class']
            levels = row['levels']
            attributes = row['attributes']

            f.write(
                "INSERT INTO characters VALUES ("
                f"'{race}', '{name}', $${proficiences}$$, '{language}', $${spells}$$, '{classs}', '{levels}', $${attributes}$$"
                ");\n"
            )

        f.close()


ninth_node = PythonOperator(
    task_id='generate_insert',
    dag=assignment_dag,
    python_callable=_insert,
    op_kwargs={
        "output_folder": "/opt/airflow/data"
    },
    trigger_rule='none_failed',
)

tenth_node = PostgresOperator(
    task_id='insert_inserts',
    dag=assignment_dag,
    postgres_conn_id='postgres_not_default',
    sql='inserts.sql',
    trigger_rule='all_success',
    autocommit=True
)

eleventh_node = DummyOperator(
    task_id='finale',
    dag=assignment_dag,
    trigger_rule='none_failed'
)

[first_node, second_node, third_node, fourth_node] >> fifth_node
fifth_node >> sixth_node >> seventh_node >> [seventh_node_a, eight_node]
seventh_node_a >> eight_node >> ninth_node >> tenth_node >> eleventh_node
