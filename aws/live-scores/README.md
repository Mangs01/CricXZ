# CricXZ Live Scores — AWS backend

This package provides a quota-safe backend for the existing CricXZ live-scores page.

## Design

- EventBridge refreshes CricketData every 20 minutes (72 scheduled hits/day).
- Lambda sanitizes the provider response and writes one encrypted S3 cache object.
- API Gateway invokes the same Lambda to read the cache.
- Website visitors never call CricketData and never receive the API key.

The CricketData API key is intentionally absent from every file in this package. Configure it only as the Lambda environment variable `CRICKETDATA_API_KEY` during deployment.

## Runtime environment variables

- `CRICKETDATA_API_KEY` — secret provider key
- `CACHE_BUCKET` — private S3 bucket name
- `ALLOWED_ORIGIN` — `https://cricxz.com`

## Files

- `lambda_function.py` — refresh and cached-response handler
- `test_lambda.py` — offline unit tests; makes no provider calls

Do not commit secrets, downloaded AWS credential CSV files, or `.env` files.
