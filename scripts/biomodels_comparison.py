"""Script to generate all pairwise comparisons of the BioModels generated
from running

``python -m mira.sources.biomodels``
"""
import pickle
from itertools import permutations
from pathlib import Path
from typing import List, Tuple

from tqdm import tqdm
from mira.dkg.web_client import is_ontological_child
from mira.sources.biomodels import BIOMODELS
from mira.metamodel import model_from_json_file
from mira.metamodel.templates import TemplateModelDelta, TemplateModel


def compare_models(
    models: List[Tuple[str, TemplateModel]],
    graph_dir: str,
) -> List[Tuple[str, str, TemplateModelDelta]]:
    """Run pairwise comparisons of models

    Parameters
    ----------
    models :
        A list of tuples of model id/name and model as a TemplateModel
    graph_dir :
        A path to a directory

    Returns
    -------
    :
        A list of tuples of model id/name of model1, model id/name of model2
        and the TemplateModelDelta for the two models.
    """
    comparisons = []
    for (id1, tm1), (id2, tm2) in tqdm(permutations(models, 2), desc="Generating Template Deltas"):
        tmd = TemplateModelDelta(template_model1=tm1, tag1=id1,
                                 template_model2=tm2, tag2=id2,
                                 refinement_function=is_ontological_child)
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

    compared_models = compare_models(
        models, graph_dir=output_folder.joinpath("graphs").as_posix()
    )

    # Pickle the files
    with output_folder.joinpath("model_diffs.pkl").open("wb") as fo:
        pickle.dump(obj=compared_models, file=fo)

    print(f"Wrote models and graphs to {output_folder}")


if __name__ == "__main__":
    main()
