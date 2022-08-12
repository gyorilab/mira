from typing import List
from itertools import count

from gromet import (
    Gromet,
    Junction,
    Wire,
    UidJunction,
    UidType,
    UidWire,
    Relation,
    UidBox,
    UidGromet,
    ModelInterface,
    UidMetadatum,
    Provenance,
    MetadatumMethod,
    get_current_datetime,
    Literal,
    Val,
)
from gromet_metadata import MetadatumJunction

from mira.modeling import Model, get_parameter_key


__all__ = ["GroMEtModel"]


class GroMEtModel:
    gromet_model: Gromet

    def __init__(self, mira_model: Model, name: str, model_name: str):
        """Initialize a GroMEtModel from a MiraModel

        Parameters
        ----------
        mira_model :
            The mira Model to convert to a Gromet
        name :
            Name of the GroMEtModel, e.g. my_petri_net
        model_name :
            A valid model name e.g. PetriNet
        """
        self.name = name
        self.model_name = model_name
        self.mira_model = mira_model
        self.created = get_current_datetime()
        self._wire_indexer = count()

        # Make the gromet model
        self._make_gromet()

    def _make_gromet(self):
        junctions: List[Junction] = []
        wires: List[Wire] = []
        boxes: List[Relation] = []

        # Add variable junctions
        for vkey, variable in self.mira_model.variables.items():
            var_meta = MetadatumJunction(
                uid=UidMetadatum(f"{vkey}_metadata"),
                provenance=Provenance(
                    method=MetadatumMethod("mira"),
                    timestamp=self.created,
                )
            )
            junctions.append(
                Junction(
                    type=UidType("Variable"),
                    name=vkey,
                    metadata=[var_meta],
                    value=variable,
                    value_type=UidType("String"),
                    uid=UidJunction(f"J:{vkey}")
                )
            )

        # Fill out junctions and wires for transitions
        for tkey, transition in self.mira_model.transitions.items():
            # Get key for rate to use instead of literal rate (a number)
            rate_key = get_parameter_key(tkey, "rate")
            cons = transition.consumed  # str?
            rate = transition.rate  # float?
            prod = transition.produced  # str?

            # Junction for consumed
            cons_id = f"J:{cons}"
            cons_meta = MetadatumJunction(
                uid=UidMetadatum(f"{cons}_metadata"),
                provenance=Provenance(
                    method=MetadatumMethod("mira"),
                    timestamp=self.created,
                ),
            )
            junctions.append(
                Junction(
                    type=UidType("Consumed"),
                    name=cons,
                    metadata=[cons_meta],
                    value=cons,
                    value_type=UidType("String"),
                    uid=UidJunction(cons_id),
                ),
            )

            # Junction for produced
            prod_id = f"J:{prod}"
            prod_meta = MetadatumJunction(
                uid=UidMetadatum(f"{prod}_metadata"),
                provenance=Provenance(
                    method=MetadatumMethod("mira"),
                    timestamp=self.created,
                ),
            )
            junctions.append(
                Junction(
                    type=UidType("Produced"),
                    name=prod,
                    metadata=[prod_meta],
                    value=prod,
                    value_type=UidType("String"),
                    uid=UidJunction(prod_id),
                ),
            )

            # Junction for transition
            rate_id = f"J:{rate_key}_{rate}"
            rate_meta = MetadatumJunction(
                uid=UidMetadatum(f"{rate}_metadata"),
                provenance=Provenance(
                    method=MetadatumMethod("mira"), timestamp=self.created
                ),
            )
            junctions.append(
                Junction(
                    type=UidType("Rate"),
                    name=tkey,
                    metadata=[rate_meta],
                    value=Literal(
                        # Assuming transition.rate is float
                        type=UidType("Float"),
                        name=None,
                        metadata=None,
                        uid=None,
                        value=Val(rate),
                    ),
                    value_type=UidType("Float"),
                    uid=UidJunction(rate_id),
                )
            )

            # Wire from consumed to rate
            in_wire_uid = f"W:{cons}_{rate_key}:w{next(self._wire_indexer)}"
            wire = Wire(
                uid=UidWire(in_wire_uid),
                src=UidJunction(cons_id),
                tgt=UidJunction(rate_id),
                type=None,
                name=None,
                metadata=None,
                value=None,
                value_type=None,
            )
            wires.append(wire)

            # Wire from rate to produced
            out_wire_uid = f"W:{rate}_{prod}:w{next(self._wire_indexer)}"
            wire = Wire(
                uid=UidWire(out_wire_uid),
                src=UidJunction(rate_id),
                tgt=UidJunction(prod_id),
                type=None,
                name=None,
                metadata=None,
                value=None,
                value_type=None,
            )
            wires.append(wire)

        junction_uids = [j.uid for j in junctions]

        model_interface = ModelInterface(
            uid=UidMetadatum(f"{self.model_name}_interface"),
            provenance=Provenance(
                method=MetadatumMethod("mira"), timestamp=self.created
            ),
            variables=junction_uids,
            parameters=[j.uid for j in junctions if j.type == "Rate"],
            initial_conditions=[j.uid for j in junctions if j.type == "State"],
        )

        pnc = Relation(
            uid=UidBox(self.name),
            type=UidType(self.model_name),
            name=self.name,
            ports=None,
            junctions=junction_uids,
            wires=[w.uid for w in wires],
            boxes=[],
            metadata=None,
        )
        boxes.append(pnc)

        g = Gromet(
            type=UidType(self.model_name),
            name=self.name,
            metadata=[model_interface],
            uid=UidGromet(f"{self.model_name}_mira_model"),
            root=pnc.uid,
            types=None,
            literals=None,
            junctions=junctions,
            ports=None,
            wires=wires,
            boxes=boxes,
            variables=None,
        )
        self.gromet_model = g
