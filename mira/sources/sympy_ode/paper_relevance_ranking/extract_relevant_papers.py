import os
from pathlib import Path
import requests
from time import sleep
import xml.etree.ElementTree as ET
from setfit import SetFitModel
import logging

HERE = Path(__file__).parent.resolve()
DATA_PATH = HERE / "extracted_papers"
POSITIVE_PATH = DATA_PATH / "positive"
DATA_PATH.mkdir(parents=True, exist_ok=True)
POSITIVE_PATH.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_setfit_model(model_path=None):
    """Load a saved SetFit model.

    Parameters
    ----------
    model_path: str
        Path to the saved model (optional)

    Returns
    -------
    : SetFitModel
        Loaded SetFit model
    """
    if model_path is None:
        model_path = HERE / "pubmed_classifier"
    logger.info(f"Loading SetFit model from: {model_path}")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at: {model_path}")
    model = SetFitModel.from_pretrained(model_path)
    return model


def extract_pmids_from_pubmed(email, max_results=10000):
    """Extract PMIDs from PubMed using E-utilities API.

    Currently retrieves papers that are filtered based on MESH terms and tags.

    Parameters
    ----------
    email : str
        Your email (required by NCBI)
    max_results : int
        Maximum number of PMIDs to retrieve

    Returns
    -------
    :
        List of PMIDs
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    # Search query to find papers relevant to epidemiological ODE models
    # Filter to include papers that mention "compartmental model", "SEIR", or "SIR model" in the title/abstract and are tagged with "epidemiology" MeSH term.
    # Can also run a looser search to get more papers that may be relevant but not tagged with the MeSH term, and rely on the classifier to filter them.
    search_query = (
        '(("compartmental model"[Title/Abstract] OR "SEIR"[Title/Abstract] OR "SIR model"[Title/Abstract]) '
        'AND ("epidemiology"[MeSH Terms] OR epidemiology[sh]))'
    )

    logger.info("Searching PubMed...")
    search_url = f"{base_url}esearch.fcgi"
    params = {
        'db': 'pubmed',
        'term': search_query,
        'retmax': max_results,
        'retmode': 'json',
        'email': email
    }
    response = requests.get(search_url, params=params)
    response.raise_for_status()
    results = response.json()
    pmids = results['esearchresult']['idlist']
    total_count = results['esearchresult']['count']
    logger.info(f"Found {total_count} total papers, retrieved {len(pmids)} PMIDs")
    return pmids


def fetch_titles_and_abstracts(pmids, email, batch_size=200):
    """Fetch titles and abstracts for PMIDs.

    Parameters
    ----------
    pmids : list
        List of PMIDs
    email : str
        Your email
    batch_size : int
        PMIDs per request

    Returns
    -------
    :
        PMID -> {title, abstract, combined_text}
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    results = {}
    total_batches = (len(pmids) + batch_size - 1) // batch_size
    for batch_idx, i in enumerate(range(0, len(pmids), batch_size)):
        batch_pmids = pmids[i:i + batch_size]
        logger.info(f"Fetching batch {batch_idx + 1}/{total_batches} ({len(batch_pmids)} papers)...")
        params = {
            'db': 'pubmed',
            'id': ','.join(batch_pmids),
            'retmode': 'xml',
            'rettype': 'abstract',
            'email': email
        }
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        for article in root.findall('.//PubmedArticle'):
            pmid_element = article.find('.//PMID')
            if pmid_element is not None:
                pmid = pmid_element.text
                title_element = article.find('.//ArticleTitle')
                title = title_element.text if title_element is not None else ""
                abstract_parts = []
                abstract_texts = article.findall('.//AbstractText')
                for abs_text in abstract_texts:
                    label = abs_text.get('Label', '')
                    text = abs_text.text if abs_text.text else ""
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
                abstract = " ".join(abstract_parts) if abstract_parts else ""
                combined_text = f"{title} {abstract}".strip()
                results[pmid] = {
                    'title': title,
                    'abstract': abstract,
                    'combined_text': combined_text
                }
        sleep(0.34)  # Rate limiting
    logger.info(f"Retrieved {len(results)} papers with abstracts")
    return results


def classify_papers(paper_data, model, batch_size=32):
    """Classify papers using title + abstract.

    Parameters
    ----------
    paper_data : dict
        PMID -> {title, abstract, combined_text}
    model : SetFit
        SetFit model
    batch_size : int
        Classification batch size

    Returns
    -------
    :
        `Classification results
    """
    positive_results = []
    negative_results = []
    pmids = list(paper_data.keys())
    texts = [paper_data[pmid]['combined_text'] for pmid in pmids]
    logger.info(f"Classifying {len(texts)} papers...")
    all_predictions = []
    all_confidences = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        confidences = model.predict_proba(batch_texts)
        predictions = confidences.argmax(dim=1).tolist()
        all_predictions.extend(predictions)
        all_confidences.extend(confidences)
    for pmid, pred, probs in zip(pmids, all_predictions, all_confidences):
        p_neg, p_pos = probs[0].item(), probs[1].item()
        result = {
            'pmid': pmid,
            'title': paper_data[pmid]['title'],
            'abstract': paper_data[pmid]['abstract'],
            'confidence': p_pos if pred == 1 else p_neg,
            'prob_positive': p_pos,
            'prob_negative': p_neg
        }
        if pred == 1:
            positive_results.append(result)
            logger.info(f"PMID {pmid}: POSITIVE (conf={p_pos:.3f})")
        else:
            negative_results.append(result)
            logger.info(f"PMID {pmid}: NEGATIVE (conf={p_neg:.3f})")
    return {
        'positive': positive_results,
        'negative': negative_results
    }


def save_results(results, output_path):
    """Save classification results with titles and abstracts."""
    positive_file = output_path / "positive_papers.tsv"
    with open(positive_file, 'w', encoding='utf-8') as f:
        f.write("PMID\tConfidence\tProb_Pos\tProb_Neg\tTitle\n")
        for item in results['positive']:
            f.write(f"{item['pmid']}\t{item['confidence']:.4f}\t{item['prob_positive']:.4f}\t{item['prob_negative']:.4f}\t{item['title']}\n")
    negative_file = output_path / "negative_papers.tsv"
    with open(negative_file, 'w', encoding='utf-8') as f:
        f.write("PMID\tConfidence\tProb_Pos\tProb_Neg\tTitle\n")
        for item in results['negative']:
            f.write(f"{item['pmid']}\t{item['confidence']:.4f}\t{item['prob_positive']:.4f}\t{item['prob_negative']:.4f}\t{item['title']}\n")
    logger.info(f"Results saved to: {output_path}")
    logger.info(f"Positive papers: {len(results['positive'])}")
    logger.info(f"Negative papers: {len(results['negative'])}")


def main():
    """Main pipeline using titles and abstracts."""

    EMAIL = "you-email-here@gmail.com"  # Replace with your email
    MAX_RESULTS = 100
    model = load_setfit_model()
    pmids = extract_pmids_from_pubmed(EMAIL, MAX_RESULTS)
    paper_data = fetch_titles_and_abstracts(pmids, EMAIL)
    results = classify_papers(paper_data, model)
    save_results(results, DATA_PATH)

if __name__ == "__main__":
    main()