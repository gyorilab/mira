import rdflib.term
from rdflib import Graph
from pathlib import Path
import os
import requests
from bs4 import BeautifulSoup

HERE = Path(__file__).parent
ONTOLOGY_FILES_DIR = HERE / 'eiffel_ttl_files'


class GraphObj:
    def __init__(self, graph, name):
        self.graph = graph
        self.name = name
        self.file_uri_list = []
        self.label_list = []


graph_obj_list = []

for file_name in os.listdir(ONTOLOGY_FILES_DIR):
    content_path = 'eiffel_ttl_files/' + file_name
    with open(content_path) as file:
        file_uri_list = []
        graph_obj = GraphObj(graph=Graph(),
                             name=file_name[:len(file_name) - 4])
        graph_obj.graph.parse(file, format='turtle')
        for subj, pred, obj in graph_obj.graph:
            if isinstance(subj, rdflib.term.URIRef):
                graph_obj.file_uri_list.append(subj)
            if isinstance(pred, rdflib.term.URIRef):
                graph_obj.file_uri_list.append(pred)
            if isinstance(obj, rdflib.term.URIRef):
                graph_obj.file_uri_list.append(obj)
        graph_obj_list.append(graph_obj)

for graph_obj in graph_obj_list:
    for uri in graph_obj.file_uri_list:
        query = """
           SELECT ?label
           WHERE {
              <""" + str(uri) + """> rdfs:label ?label.
           }
           """
        query_result = graph_obj.graph.query(query)

        for res in query_result:
            graph_obj.label_list.append(res[0])
    with open(graph_obj.name + '.txt', 'w', newline='') as file:
        # writer = csv.writer(file)
        for label in graph_obj.label_list:
            file.write(str(label) + '\n')
