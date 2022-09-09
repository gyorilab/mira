"""
This module contains a way to deploy a custom instance of the :mod:`bioregistry` (https://bioregistry.io)
application based on MIRA's domain knowledge graph's prefixes.

Run the web application with ``python -m mira.dkg.metaregistry``. Note that this requires either the environment
variables to connect with the :class:`mira.dkg.client.Neo4jclient` or the appropriate :class:`pystow` configuration.
"""
