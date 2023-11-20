from rdflib import Graph
from pathlib import Path
import os
import csv
import requests

HERE = Path(__file__).parent
ONTOLOGY_FILES_DIR = HERE / 'eiffel_ttl_files'
RESULTS_DIR = HERE / 'Results'
ECV_KB_URL = ('https://raw.githubusercontent.com/benmomo/'
              'eiffel-ontology/main/ontology/ecv-kb.ttl')
EO_KB_URL = ('https://raw.githubusercontent.com/benmomo/'
             'eiffel-ontology/main/ontology/eo-kb.ttl')
SDG_SERIES_URL = ('https://raw.githubusercontent.com/benmomo/eiffel'
                  '-ontology/main/ontology/sdg-kos-series-2019-Q2-G-01.ttl')
SDG_GOAL_URL = ('https://raw.githubusercontent.com/benmomo/eiffel-ontology/'
                'main/ontology/sdg-kos-goals-targets-indicators.ttl')


class GraphObj:
    def __init__(self, graph, name):
        self.graph = graph
        self.name = name
        self.file_uri_list = []
        self.info_list = []
        self.relationship_list = []


def get_store_graphs():
    os.makedirs(ONTOLOGY_FILES_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    ecv_kb_request = requests.get(ECV_KB_URL)
    with open(str(ONTOLOGY_FILES_DIR) + '/' + 'ecv-kb.ttl', 'w') as file:
        file.write(ecv_kb_request.text)

    eo_kb_request = requests.get(EO_KB_URL)
    with open(str(ONTOLOGY_FILES_DIR) + '/' + 'eo-kb.ttl', 'w') as file:
        file.write(eo_kb_request.text)

    sgd_series_request = requests.get(SDG_SERIES_URL)
    with open(str(ONTOLOGY_FILES_DIR) + '/' +
              'sdg-kos-series-2019-Q2-G-01.ttl',
              'w') as file:
        file.write(sgd_series_request.text)

    sdg_goal_request = requests.get(SDG_GOAL_URL)
    with open(str(ONTOLOGY_FILES_DIR) +
              '/sdg-kos-goals-targets-indicators.ttl',
              'w') as file:
        file.write(sdg_goal_request.text)

    graph_obj_map = {}
    for file_name in os.listdir(ONTOLOGY_FILES_DIR):
        content_path = 'eiffel_ttl_files/' + file_name
        with open(content_path) as file:
            graph_obj_ = GraphObj(graph=Graph(),
                                  name=file_name[:len(file_name) - 4])
            graph_obj_.graph.parse(file, format='turtle')
            graph_obj_map[file_name] = graph_obj_
    return graph_obj_map


def process_ecv(graph_obj):
    ecv_query = """
               SELECT DISTINCT ?individual
               (GROUP_CONCAT(?dataSource; SEPARATOR="|") AS ?dataSources)
               ?domain
               (GROUP_CONCAT(?ecvProduct; SEPARATOR="|") AS ?ecvProducts)
               (GROUP_CONCAT(?ecvSteward; SEPARATOR="|") AS ?ecvStewards)
               ?scientificArea
               ?ecvDescription
               ?ecvFactsheetLink ?ecvIconLink ?ecvName ?label
               WHERE {
                   ?individual rdf:type :ECV .
                      OPTIONAL { ?individual :hasDataSource ?dataSource . }
                      OPTIONAL { ?individual :hasDomain ?domain . }
                      OPTIONAL { ?individual :hasECVProduct ?ecvProduct . }
                      OPTIONAL { ?individual :hasECVSteward ?ecvSteward . }
                      OPTIONAL { ?individual :hasScientificArea ?scientificArea.}
                      OPTIONAL { ?individual :ecvDescription ?ecvDescription.}
                      OPTIONAL { ?individual :ecvFactsheetLink ?ecvFactsheetLink.}
                      OPTIONAL { ?individual :ecvIconLink ?ecvIconLink . }
                      OPTIONAL { ?individual :ecvName ?ecvName . }
                      OPTIONAL { ?individual rdfs:label ?label . }
               }
               GROUP BY ?individual ?hasDomain
               ?scientificArea ?ecvDescription ?ecvFactsheetLink
               ?ecvIconLink ?ecvName ?label
               """
    ecv_query_result_dict = graph_obj.graph.query(ecv_query)

    for res in ecv_query_result_dict:
        graph_obj.info_list.append(
            (str(res['individual']), str(res['label']),
             str(res['ecvDescription'])))

        graph_obj.relationship_list.append((str(res['individual']),
                                            str(res['label']),
                                            str(res['dataSources']),
                                            str(res['domain']),
                                            str(res['ecvProducts']),
                                            str(res['ecvStewards']),
                                            str(res['scientificArea']),
                                            str(res['ecvFactsheetLink']),
                                            str(res['ecvIconLink'])))
    ecv_product_query = """
            SELECT DISTINCT ?individual ?label ?description
            WHERE{
            ?individual rdf:type :ECVProduct;
                 dc:description ?description;
                 rdfs:label ?label.
            FILTER(LANG(?label) = "en" && LANG(?description) = "en")
            }
            """
    ecv_product_query_dict = graph_obj.graph.query(ecv_product_query)
    for res in ecv_product_query_dict:
        graph_obj.info_list.append(
            (str(res['individual']), str(res['label']),
             str(res['description'])))

    with open(str(RESULTS_DIR) + '/' + graph_obj.name + ' information.csv',
              'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['individual URI', 'Label', 'Description'])
        for row in graph_obj.info_list:
            csv_out.writerow(row)

    with open(str(RESULTS_DIR) + '/' + graph_obj.name + ' relation.csv',
              'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['Individual URI', 'Label', 'Data Sources', 'Domain',
                          'ECV Products',
                          'ECV Stewards', 'scientific Area', 'ECV Fact Sheet '
                                                             'Link',
                          'EVC Icon Link'])
        for row in graph_obj.relationship_list:
            csv_out.writerow(row)


def process_eo(graph_obj_eo):
    eo_query = """
               SELECT DISTINCT ?individual ?type ?description ?label
               WHERE {
                    ?individual rdf:type ?type 
                    FILTER (?type = :Domain || ?type = :Market || ?type=
                    :ThematicView)
                    ?individual rdfs:label ?label.
                    ?individual dc:description ?description.
               }
               """
    eo_query_result_dict = graph_obj_eo.graph.query(eo_query)
    for res in eo_query_result_dict:
        graph_obj_eo.info_list.append(
            (str(res['individual']), str(res['label']),
             str(res['description'])))

    with open(str(RESULTS_DIR) + '/' + graph_obj_eo.name + ' information.csv',
              'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['individual URI', 'Label', 'Description'])
        for row in graph_obj_eo.info_list:
            csv_out.writerow(row)


def process_sdg_goals(graph_obj_sdg_goals):
    sdg_goal_query = """
                    SELECT DISTINCT ?subject ?label
                    WHERE {
                        ?subject skos:prefLabel ?label.
                        FILTER(LANG(?label) = 'en')
                    }
                    """
    sdg_goals_query_result_dict = graph_obj_sdg_goals.graph.query(
        sdg_goal_query)
    for res in sdg_goals_query_result_dict:
        graph_obj_sdg_goals.info_list.append(
            (str(res['subject']), str(res['label'])))
    with open(str(RESULTS_DIR) + '/' + graph_obj_sdg_goals.name + ' '
                                        'information.csv','w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['Subject', 'Label'])
        for row in graph_obj_sdg_goals.info_list:
            csv_out.writerow(row)


def process_sdg_series(graph_obj):
    sdg_goal_query = """
                        SELECT DISTINCT ?subject ?label
                        WHERE {
                            ?subject skos:prefLabel ?label.
                            FILTER(LANG(?label) = 'en')
                        }
                        """
    result_dict = graph_obj.graph.query(
        sdg_goal_query)
    for res in result_dict:
        graph_obj.info_list.append((str(res['subject']), str(res['label'])))
    with open(str(RESULTS_DIR) + '/' + graph_obj.name + ' information.csv',
              'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['Subject', 'Label'])
        for row in graph_obj.info_list:
            csv_out.writerow(row)


def main():
    graph_obj_map = get_store_graphs()
    process_ecv(graph_obj_map['ecv-kb.ttl'])
    process_eo(graph_obj_map['eo-kb.ttl'])
    process_sdg_goals(graph_obj_map['sdg-kos-goals-targets-indicators.ttl'])
    process_sdg_series(graph_obj_map['sdg-kos-series-2019-Q2-G-01.ttl'])


if __name__ == "__main__":
    main()
