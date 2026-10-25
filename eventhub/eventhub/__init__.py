"""EventHub: a modular-monolith ticketing system (Python / Flask / SQLite).

Each C4 component lives in its own module and can be imported and unit tested
without the Flask application:

    database, identity, catalog, pricing, inventory, audit, purchasing,
    administration

The ``boundary`` package (Flask blueprints) is the only layer that talks HTTP.
"""
