#!/bin/sh

disease-normalizer check-db
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo "Data already exists. Skipping ETL."
else
  echo "Database status check failed. Running ETL..."
  disease-normalizer update --all --normalize
  echo "ETL completed."
fi

exec uvicorn disease.main:app  --port 80 --host 0.0.0.0
