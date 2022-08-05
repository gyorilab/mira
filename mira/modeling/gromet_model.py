from typing import List

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

from . import Model, get_parameter_key


class GroMEtModel:
    gromet_model: Gromet

    def __init__(self, mira_model: Model, name: str):
        self.name = name
        self.mira_model = mira_model
        self.created = get_current_datetime()

        # Make the gromet model
        self._make_gromet()

    def _make_gromet(self):
        junctions: List[Junction] = []
        wires: List[Wire] = []
        boxes: List[Relation] = []
        added_wires = set()

        # Fill out wires for transitions
        for tkey, transition in self.mira_model.transitions.items():
            rate_key = get_parameter_key(tkey, "rate")
            cons = transition.consumed  # str?
            rate = transition.rate  # float?
            prod = transition.produced  # str?

            # Junction for transition
            jxn_meta = MetadatumJunction(
                uid=UidMetadatum(f"{rate}_metadata"),
                provenance=Provenance(
                    method=MetadatumMethod("mira"), timestamp=self.created
                ),
            )
            junction_id = f"J:{rate_key}"
            junctions.append(
                Junction(
                    type=UidType("Rate"),
                    name=tkey,
                    metadata=[jxn_meta],
                    value=Literal(
                        type=UidType("Float"),
                        name=None,
                        metadata=None,
                        uid=None,
                        value=Val(rate),  # Assuming transition.rate is float
                    ),
                    value_type=UidType("Float"),
                    uid=UidJunction(junction_id),
                )
            )

            # Wire from consumed to rate
            cr_uid = f"W:{cons}_{rate_key}:w0"
            assert cr_uid not in added_wires, "did not pass sanity check 1"
            wire = Wire(
                uid=UidWire(cr_uid),
                src=UidJunction(f"J:{cons}"),
                tgt=UidJunction(junction_id),
                type=None,
                name=None,
                metadata=None,
                value=None,
                value_type=None,
            )
            wires.append(wire)
            added_wires.add(cr_uid)

            # Wire from rate to produced
            rp_uid = f"W:{rate}_{prod}:w1"
            assert rp_uid not in added_wires, "did not pass sanity check 2"
            wire = Wire(
                uid=UidWire(rp_uid),
                src=UidJunction(junction_id),
                tgt=UidJunction(f"J:{prod}"),
                type=None,
                name=None,
                metadata=None,
                value=None,
                value_type=None,
            )
            wires.append(wire)
            added_wires.add(rp_uid)

        junction_uids = [j.uid for j in junctions]

        model_interface = ModelInterface(
            uid=UidMetadatum(f"{self.name}_model_interface"),
            provenance=Provenance(
                method=MetadatumMethod("mira_model"), timestamp=self.created
            ),
            variables=junction_uids,
            parameters=[j.uid for j in junctions if j.type == "Rate"],
            initial_conditions=[j.uid for j in junctions if j.type == "State"],
        )

        pnc = Relation(
            uid=UidBox(self.name),
            type=UidType("PetriNetClassic"),
            name=self.name,
            ports=None,
            junctions=junction_uids,
            wires=[w.uid for w in wires],
            boxes=[],
            metadata=None,
        )
        boxes.append(pnc)

        g = Gromet(
            type=UidType("PetriNetClassic"),
            name=self.name,
            metadata=[model_interface],
            uid=UidGromet(f"{self.name}_mira_model"),
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
