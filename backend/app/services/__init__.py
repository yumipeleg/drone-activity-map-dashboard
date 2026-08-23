# Thin query/business-operation functions that sit between API routes and
# the database (route -> service -> SQLAlchemy). The pipeline runner
# (app/pipeline/runner.py) is invoked directly by its route instead, since
# it already owns its own DB session and orchestration.
