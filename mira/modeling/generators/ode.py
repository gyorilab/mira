from ...metamodel import *
from .. import Model


class OdeGenerator:
    def __init__(self, model: Model):
        self.model = model


    def generate(self):