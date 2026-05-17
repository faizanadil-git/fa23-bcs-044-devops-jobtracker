// init-mongo.js
// JobTrack Database Initialization Script
// FA23-BCS-044
// Runs automatically when MongoDB container starts for the first time

db = db.getSiblingDB('job_tracker');

// Create collections
db.createCollection('users');
db.createCollection('applications');
db.createCollection('debriefs');

// Create indexes for faster queries
db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });
db.applications.createIndex({ "user_id": 1 });
db.debriefs.createIndex({ "user_id": 1 });

print('JobTrack database initialized successfully');
