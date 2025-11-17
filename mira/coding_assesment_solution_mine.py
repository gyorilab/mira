import requests
import json
import sys
from lxml import etree

PUBMED_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
GILDA_ANNOTATE_ENDPOINT = "https://grounding.indra.bio/annotate"

def get_abstract_from_pubmed(pmid: int):
    # xml is default return mode
    response = requests.get(PUBMED_URL, params={
        "db": "pubmed",
        "id": pmid
    })
    xml_text = response.content.decode("utf-8")
    try:
        tree = etree.fromstring(xml_text)
    except ValueError:
        raise ValueError("Please use a valid pmid ")
    abstract_text_list = tree.xpath(
        ".//PubmedArticle/MedlineCitation/Article/Abstract/AbstractText//text()")
    full_abstract = ''.join(abstract_text_list)
    if not full_abstract:
        raise ValueError("The article doesn't have an abstract")
    return full_abstract



def annotate_abstract_with_gilda(abstract_text: str):
    response = requests.post(GILDA_ANNOTATE_ENDPOINT, json={"text": abstract_text})
    annotations = response.json()
    return annotations

def save_annotation_data(annotations, pmid):
    with open(f"{pmid}.json", 'w') as file:
        json.dump(annotations, file, indent=4)



if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("Didn't pass in an id")
    if len(sys.argv) > 2:
        raise ValueError("Only pass in a single pmid")
    pmid = sys.argv[1]
    if "." in pmid:
        raise ValueError("Only pass an integer")
    try:
        pmid = int(pmid)
    except ValueError:
        raise ValueError("Please only pass in an integer")
    abstract_text = get_abstract_from_pubmed(pmid)
    annotations = annotate_abstract_with_gilda(abstract_text)
    save_annotation_data(annotations, pmid)



