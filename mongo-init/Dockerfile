# Dockerfile.db
# JobTrack Database — MongoDB
# FA23-BCS-044

FROM mongo:7.0

# Set default database name
ENV MONGO_INITDB_DATABASE=job_tracker

# Copy initialization script
# This runs automatically when the container starts for the first time
COPY init-mongo.js /docker-entrypoint-initdb.d/

# MongoDB default port
EXPOSE 27017
