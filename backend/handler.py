"""
AWS Lambda entry point via Mangum.
This wraps the FastAPI app so it can run as a Lambda function
behind API Gateway or a Function URL.
"""
from mangum import Mangum
from app.main import app

handler = Mangum(app, lifespan="off")
