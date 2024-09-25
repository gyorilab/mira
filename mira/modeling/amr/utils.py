def add_metadata_annotations(metadata, model):
    if not model.template_model.annotations:
        metadata['annotations'] = {}
        return
    annotations_subset = {
        k: (str(v) if k in ["time_start", "time_end"] and v is not None else v)
        for k, v in model.template_model.annotations.model_dump().items()
        if k not in ["name", "description"]
        # name and description already have a privileged place
        # in the petrinet schema so don't get added again
    }
    if annotations_subset:
        metadata['annotations'] = annotations_subset
