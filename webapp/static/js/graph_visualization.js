draw = () => {
    const config = {
        containerId: "viz",
        neo4j: {
            serverUrl: "bolt://localhost:7687",
            serverUser: "airflow",
            serverPassword: "airflow",
        },
        labels: {
            "Hike": {
                label: "name",
                // shape: "dot",
                // borderWidth: 100,
                // font: {
                //     size: 14,
                //     align: "top"
                // }
            },

        },
        relationships: {
            'animals': {
                value: "name"
            }
        },
        initialCypher: "MATCH (n)-[r]-() RETURN n, r LIMIT 25"
    };

    neoViz = new NeoVis.default(config);
    neoViz.render();
};
