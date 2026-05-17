# Dockerfile.frontend
# JobTrack Frontend — Nginx reverse proxy
# FA23-BCS-044
# Acts as the entry point — forwards all requests to Flask backend

FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom nginx config
COPY nginx.conf /etc/nginx/conf.d/jobtrack.conf

# Expose port 80 for public access
EXPOSE 80

# Nginx starts automatically as the base image CMD
