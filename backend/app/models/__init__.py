# SQLAlchemy ORM models. Importing the model modules here (rather than only
# where they're used) ensures Base.metadata — and therefore Alembic
# autogenerate — always sees every table from a single import of this
# package.

from app.models.drone_telemetry import DroneTelemetry  # noqa: F401
from app.models.pipeline_run import PipelineRun  # noqa: F401
