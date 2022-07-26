from typing import List

from mira.metamodel import Template


class Model:
    def __init__(self, templates=List[Template]):
        self.templates = templates
