"""Script to generate all pairwise comparisons of the BioModels generated
from running

``python -m mira.sources.biomodels``
"""
import pickle
from itertools import combinations
from pathlib import Path
from typing import List, Tuple, Optional, Set
from tqdm import tqdm

from mira.sources.biomodels import BIOMODELS
from mira.metamodel import model_from_json_file
from mira.metamodel.templates import TemplateModelDelta, TemplateModel, RefinementClosure


def compare_models(
    models: List[Tuple[str, TemplateModel]],
    graph_dir: str,
    transitive_closure: Optional[Set[Tuple[str, str]]] = None,
) -> List[Tuple[str, str, TemplateModelDelta]]:
    """Run pairwise comparisons of models

    Parameters
    ----------
    models :
        A list of tuples of model id/name and model as a TemplateModel
    graph_dir :
        A path to a directory
    transitive_closure :
        Provide a transitive closure set to initialize a RefinementClosure
        class with. If not provided, an attempt will be made to get a new
        one from the DKG

    Returns
    -------
    :
        A list of tuples of model id/name of model1, model id/name of model2
        and the TemplateModelDelta for the two models.
    """
    # Load RefinementClosure from a transitive_closure
    if transitive_closure is None:
        from mira.dkg.client import Neo4jClient

        client = Neo4jClient()
        transitive_closure = client.get_transitive_closure()

    refinement_closure = RefinementClosure(transitive_closure)

    comparisons = []
    model_pairs = list(combinations(models, 2))
    for (id1, tm1), (id2, tm2) in tqdm(model_pairs,
                                       desc="Generating Template Deltas"):
        tmd = TemplateModelDelta(
            template_model1=tm1,
            tag1=id1,
            template_model2=tm2,
            tag2=id2,
            refinement_function=refinement_closure.is_ontological_child,
        )
        outpath = Path(graph_dir).joinpath(f"delta_{id1}_{id2}.png").as_posix()
        tmd.draw_graph(path=outpath)
        comparisons.append((id1, id2, tmd))

    return comparisons


def main():
    # Setup
    base_folder = BIOMODELS.module("models").base
    output_folder = BIOMODELS.module("model_diffs").base

    # Load model jsons
    models = []
    for path in base_folder.glob("*/*.json"):
        # Check if file exsits
        if not path.is_file():
            print(f"No such file {path}")
            continue

        # Load model
        template_model = model_from_json_file(path.as_posix())
        model_id = path.name.split(".")[0]
        models.append((model_id, template_model))

    if len(models) <= 1:
        print(
            "2 or more models need to be loaded to compare them. Was "
            "`python -m mira.sources.biomodels` run before this script?"
        )
        return

    # Load transitive closure from pickle if provided
    if tc_pickle_path:
        tc = pickle.load(open(tc_pickle_path, "rb"))
    else:
        tc = None

    graph_dir = output_folder.joinpath("graphs")
    graph_dir.mkdir(parents=True, exist_ok=True)
    compared_models = compare_models(models, graph_dir=graph_dir.as_posix(), transitive_closure=tc)

    # Pickle the list of TemplateModelDelta objects with the model ids
    with output_folder.joinpath("model_diffs.pkl").open("wb") as fo:
        pickle.dump(obj=compared_models, file=fo)

    print(f"Wrote models and graphs to {output_folder}")


if __name__ == "__main__":
    import sys

    # Get path to pickled transitive closure
    tc_pickle_path = sys.argv[1] if len(sys.argv) > 1 else None
    if tc_pickle_path:
        print(f"Loading transitive closure from {tc_pickle_path}")
    main()
