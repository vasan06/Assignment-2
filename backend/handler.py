"""
AWS Lambda entry point.

Mangum adapts FastAPI's ASGI interface to the Lambda event/context model.
API Gateway or a Lambda Function URL both work — no extra configuration needed.
"""
from mangum import Mangum
from app.main import app

handler = Mangum(app, lifespan="off")
