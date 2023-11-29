from rdflib import Graph
from pathlib import Path
import os
import csv
import requests
from curies import Converter
from rdflib.term import URIRef

HERE = Path(__file__).parent
ONTOLOGY_FILES_DIR = HERE / 'eiffel_ttl_files'
RESULTS_DIR = HERE / 'sql_query_spreadsheet_results'
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
        self.class_list = []


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


def process_ecv(graph_obj, converter):
    info_query = """
               SELECT DISTINCT ?individual ?description ?label
                WHERE {
                    {
                        ?individual rdf:type ?type .
                        ?individual rdfs:label ?label .
                        OPTIONAL{?individual dc:description ?description} .
                    }
                }
               """
    ecv_query_result_dict = graph_obj.graph.query(info_query)

    for res in ecv_query_result_dict:
        individual_uri = str(res['individual'])
        compressed_individual = converter.compress(individual_uri)
        description_str = res['description']
        if description_str is None:
            description_str = ''
        graph_obj.info_list.append(
            (compressed_individual, individual_uri, str(res['label']),
             description_str))

    relationship_query = """
        SELECT ?subject ?predicate ?object ?label
        WHERE{
        {?subject ?predicate ?object}. 
        ?subject rdfs:label ?label 
        FILTER (isIRI(?object) && (CONTAINS(STR(?predicate), "ecv")))
        }
    """
    relationship_results_dict = graph_obj.graph.query(relationship_query)

    for res in relationship_results_dict:
        subject_uri = str(res['subject'])
        compressed_subject = converter.compress(subject_uri)
        predicate_uri = str(res['predicate'])
        compressed_predicate = converter.compress(predicate_uri)
        object_uri = str(res['object'])
        compressed_object = converter.compress(object_uri)
        graph_obj.relationship_list.append((str(res['label']),
                                            compressed_subject,
                                            subject_uri,
                                            compressed_predicate,
                                            predicate_uri,
                                            compressed_object, object_uri))

    unique_predicate_query = """
            SELECT DISTINCT ?predicate
            WHERE {
              ?subject ?predicate ?object.
            }
            """

    unique_predicate_results = graph_obj.graph.query(unique_predicate_query)
    unique_predicates = list(
        set(str(row['predicate']) for row in
            unique_predicate_results.bindings))

    with open(str(RESULTS_DIR) + '/' + graph_obj.name + ' information.csv',
              'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['Individual', 'Individual URI', 'Label',
                          'Description'])
        for row in graph_obj.info_list:
            csv_out.writerow(row)

    with open(str(RESULTS_DIR) + '/' + graph_obj.name + ' relation.csv',
              'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['Label', 'Subject', 'Subject URI', 'Predicate',
                          'Predicate URI', 'Object', 'Object URI'])

        for row in graph_obj.relationship_list:
            csv_out.writerow(row)

    with open(str(RESULTS_DIR) + '/' + graph_obj.name +
              ' unique_predicates.txt', 'w') as file:
        file.write(
            f'Number of unique predicates: {len(unique_predicates)}\n\n')

        # Write each unique predicate to the file
        for predicate in unique_predicates:
            file.write(f'{predicate}\n')


def process_eo(graph_obj, converter):
    info_query = """
           SELECT DISTINCT ?individual ?type ?description ?label
           WHERE {
               {
                    ?individual rdf:type ?type.
                    ?individual rdfs:label ?label.
                    OPTIONAL{?individual dc:description ?description.}
               }
                UNION
                {
                    ?individual rdf:type :Area .
                    ?individual rdfs:label ?label .
                    ?individual :areaKeyWords ?description .
                }
            }
            """

    eo_query_result_dict = graph_obj.graph.query(info_query)
    for res in eo_query_result_dict:
        entity_uri = str(res['individual'])
        compressed_entity = converter.compress(entity_uri)
        description_str = res['description']
        if description_str is None:
            description_str = ''
        graph_obj.info_list.append(
            (compressed_entity, str(res['individual']), str(res['label']),
             description_str))

    relationship_query = """
            SELECT ?subject ?predicate ?object ?label
            WHERE{
            {?subject ?predicate ?object}. 
            ?subject rdfs:label ?label 
            FILTER (isIRI(?object) && (CONTAINS(STR(?predicate), "eotaxonomy")))
            }
        """

    relationship_results_dict = graph_obj.graph.query(relationship_query)
    for res in relationship_results_dict:
        subject_uri = str(res['subject'])
        compressed_subject = converter.compress(subject_uri)
        predicate_uri = str(res['predicate'])
        compressed_predicate = converter.compress(predicate_uri)
        object_uri = str(res['object'])
        compressed_object = converter.compress(object_uri)
        graph_obj.relationship_list.append((str(res['label']),
                                            compressed_subject,
                                            subject_uri,
                                            compressed_predicate,
                                            predicate_uri,
                                            compressed_object, object_uri))

    unique_predicate_query = """
                SELECT DISTINCT ?predicate
                WHERE {
                  ?subject ?predicate ?object.
                }
                """

    unique_predicate_results = graph_obj.graph.query(unique_predicate_query)
    unique_predicates = list(
        set(str(row['predicate']) for row in
            unique_predicate_results.bindings))

    with open(str(RESULTS_DIR) + '/' + graph_obj.name + ' information.csv',
              'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['individual', 'individual URI', 'Label',
                          'Description'])
        for row in graph_obj.info_list:
            csv_out.writerow(row)

    with open(str(RESULTS_DIR) + '/' + graph_obj.name + ' relation.csv',
              'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['Label', 'Subject', 'Subject URI', 'Predicate',
                          'Predicate URI', 'Object', 'Object URI'])

        for row in graph_obj.relationship_list:
            csv_out.writerow(row)

    with open(str(RESULTS_DIR) + '/' + graph_obj.name +
              ' unique_predicates.txt', 'w') as file:
        file.write(
            f'Number of unique predicates: {len(unique_predicates)}\n\n')

        # Write each unique predicate to the file
        for predicate in unique_predicates:
            file.write(f'{predicate}\n')


def process_sdg_goals(graph_obj, converter):
    info_query = """
                SELECT DISTINCT ?subject ?label
                WHERE {
                    ?subject skos:prefLabel ?label.
                    FILTER(LANG(?label) = 'en')
                }
                """
    sdg_goals_query_result_dict = graph_obj.graph.query(
        info_query)
    for res in sdg_goals_query_result_dict:
        subject_uri = str(res['subject'])
        compressed_subject = converter.compress(subject_uri)
        graph_obj.info_list.append(
            (compressed_subject, str(res['subject']), str(res['label'])))

    relationship_query = """
              SELECT ?subject ?predicate ?object ?label
              WHERE{
              {?subject ?predicate ?object}. 
              ?subject skos:prefLabel ?label. 
              FILTER(LANG(?label) = 'en')
              FILTER (?predicate NOT IN (skos:inScheme, skos:exactMatch,
              sdgo:tier, skos:topConceptOf) && isIRI(?object) &&
             (CONTAINS(STR(?predicate), "sdg") || CONTAINS(STR(?predicate), 
             "skos"))
             )
            }
          """

    relationship_results_dict = graph_obj.graph.query(relationship_query)
    for res in relationship_results_dict:
        subject_uri = str(res['subject'])
        compressed_subject = converter.compress(subject_uri)
        predicate_uri = str(res['predicate'])
        compressed_predicate = converter.compress(predicate_uri)
        object_uri = str(res['object'])
        compressed_object = converter.compress(object_uri)
        graph_obj.relationship_list.append((str(res['label']),
                                            compressed_subject,
                                            subject_uri,
                                            compressed_predicate,
                                            predicate_uri,
                                            compressed_object, object_uri))

    unique_predicate_query = """
           SELECT DISTINCT ?predicate
           WHERE {
             ?subject ?predicate ?object.
           }
           """

    unique_predicate_results = graph_obj.graph.query(unique_predicate_query)
    unique_predicates = list(
        set(str(row['predicate']) for row in
            unique_predicate_results.bindings))

    with open(str(RESULTS_DIR) + '/' + graph_obj.name
              + ' ''information.csv', 'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['Subject', 'Subject URI', 'Description'])
        for row in graph_obj.info_list:
            csv_out.writerow(row)

    with open(str(RESULTS_DIR) + '/' + graph_obj.name + ' relation.csv',
              'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['Label', 'Subject', 'Subject URI', 'Predicate',
                          'Predicate URI', 'Object', 'Object URI'])

        for row in graph_obj.relationship_list:
            csv_out.writerow(row)

    with open(str(RESULTS_DIR) + '/' + graph_obj.name +
              ' unique_predicates.txt', 'w') as file:
        file.write(
            f'Number of unique predicates: {len(unique_predicates)}\n\n')

        # Write each unique predicate to the file
        for predicate in unique_predicates:
            file.write(f'{predicate}\n')


def process_sdg_series(graph_obj, converter):
    info_query = """
                        SELECT DISTINCT ?subject ?label
                        WHERE {
                            ?subject skos:prefLabel ?label.
                            FILTER(LANG(?label) = 'en')
                        }
                        """
    result_dict = graph_obj.graph.query(
        info_query)
    for res in result_dict:
        subject_uri = str(res['subject'])
        compressed_subject = converter.compress(subject_uri)
        graph_obj.info_list.append((compressed_subject, str(res['subject']),
                                    str(res['label'])))

    relationship_query = """
                  SELECT ?subject ?predicate ?object ?label
                  WHERE{
                  {?subject ?predicate ?object}. 
                  ?subject skos:prefLabel ?label. 
                  FILTER(LANG(?label) = 'en')
                  FILTER (?predicate NOT IN (skos:inScheme, skos:exactMatch,
                  sdgo:tier, skos:topConceptOf) && isIRI(?object) &&
                 (CONTAINS(STR(?predicate), "sdg") || CONTAINS(STR(?predicate), 
                 "skos"))
                 )
                }
              """

    relationship_results_dict = graph_obj.graph.query(relationship_query)
    for res in relationship_results_dict:
        subject_uri = str(res['subject'])
        compressed_subject = converter.compress(subject_uri)
        predicate_uri = str(res['predicate'])
        compressed_predicate = converter.compress(predicate_uri)
        object_uri = str(res['object'])
        compressed_object = converter.compress(object_uri)
        graph_obj.relationship_list.append((str(res['label']),
                                            compressed_subject,
                                            subject_uri,
                                            compressed_predicate,
                                            predicate_uri,
                                            compressed_object, object_uri))

    unique_predicate_query = """
      SELECT DISTINCT ?predicate
      WHERE {
        ?subject ?predicate ?object.
      }
      """

    unique_predicate_results = graph_obj.graph.query(unique_predicate_query)
    unique_predicates = list(
        set(str(row['predicate']) for row in
            unique_predicate_results.bindings))

    with open(str(RESULTS_DIR) + '/' + graph_obj.name + ' information.csv',
              'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['Subject', 'Subject URI', 'Description'])
        for row in graph_obj.info_list:
            csv_out.writerow(row)

    with open(str(RESULTS_DIR) + '/' + graph_obj.name + ' relation.csv',
              'w') as file:
        csv_out = csv.writer(file)
        csv_out.writerow(['Label', 'Subject', 'Subject URI', 'Predicate',
                          'Predicate URI', 'Object', 'Object URI'])

        for row in graph_obj.relationship_list:
            csv_out.writerow(row)

    with open(str(RESULTS_DIR) + '/' + graph_obj.name +
              ' unique_predicates.txt', 'w') as file:
        file.write(
            f'Number of unique predicates: {len(unique_predicates)}\n\n')

        # Write each unique predicate to the file
        for predicate in unique_predicates:
            file.write(f'{predicate}\n')


def main():
    converter = Converter.from_prefix_map(
        {
            "ecv": "http://purl.org/eiffo/ecv#",
            "eotaxonomy": "http://purl.org/eiffo/eotaxonomy#",
            "sdg": "http://metadata.un.org/sdg/",
            "sdgo": "http://metadata.un.org/sdg/ontology#",
            "skos": "http://www.w3.org/2004/02/skos/core#"
        }
    )

    graph_obj_map = get_store_graphs()
    process_ecv(graph_obj_map['ecv-kb.ttl'], converter)
    process_eo(graph_obj_map['eo-kb.ttl'], converter)
    process_sdg_goals(graph_obj_map['sdg-kos-goals-targets-indicators.ttl'],
                      converter)
    process_sdg_series(graph_obj_map['sdg-kos-series-2019-Q2-G-01.ttl'],
                       converter)


if __name__ == "__main__":
    main()
