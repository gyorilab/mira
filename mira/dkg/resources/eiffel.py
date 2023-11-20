from rdflib import Graph
from pathlib import Path
import os
import csv

HERE = Path(__file__).parent
ONTOLOGY_FILES_DIR = HERE / 'eiffel_ttl_files'


class GraphObj:
    def __init__(self, graph, name):
        self.graph = graph
        self.name = name
        self.file_uri_list = []
        self.info_list = []
        self.relationship_list = []


graph_obj_list = []

for file_name in os.listdir(ONTOLOGY_FILES_DIR):
    content_path = 'eiffel_ttl_files/' + file_name
    with open(content_path) as file:
        file_uri_list = []
        graph_obj = GraphObj(graph=Graph(),
                             name=file_name[:len(file_name) - 4])
        graph_obj.graph.parse(file, format='turtle')
        graph_obj_list.append(graph_obj)

for graph_obj in graph_obj_list:
    label_query = """
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
    label_query_result = graph_obj.graph.query(label_query)
    for res in label_query_result:
        graph_obj.info_list.append((str(res['individual']), str(res['label']),
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

    with open(graph_obj.name + ' information.csv', 'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['individual URI', 'Label', 'Description'])
        for row in graph_obj.info_list:
            csv_out.writerow(row)

    with open(graph_obj.name + ' relation.csv', 'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['Individual URI', 'Label', 'Data Sources', 'Domain',
                          'ECV Products',
                          'ECV Stewards', 'scientific Area', 'ECV Fact Sheet '
                                                             'Link',
                          'EVC Icon Link'])
        for row in graph_obj.relationship_list:
            csv_out.writerow(row)
