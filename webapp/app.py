# from flask import Flask, request, render_template
# from neo4j import GraphDatabase

# app = Flask(__name__)

# neo4j_url = "bolt://neo:7687"
# driver = GraphDatabase.driver(neo4j_url, auth=("airflow", "airflow"))

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/run_query', methods=['POST'])
# def run_query():
#     query = request.form['query']
#     result = execute_query(query)
#     return render_template('result.html', result=result)

# def execute_query(query):
#     with driver.session() as session:
#         result = session.run(query)
#         return result.data()


from flask import Flask, render_template, request, send_from_directory
from neo4j import GraphDatabase

app = Flask(__name__)

uri = "bolt://neo:7687"  # Update with your Neo4j server details
user = "airflow"
password = "airflow"


class Neo4jService:
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def execute_query(self, query):
        with self._driver.session() as session:
            result = session.run(query)
            return result.data()


neo4j_service = Neo4jService(uri, user, password)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('static/js', filename)


@app.route('/query', methods=['POST'])
def query():
    pass
    # query_text = request.form.get('query')
    # result = neo4j_service.execute_query(query_text)
    # return render_template('result.html', result=result)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
