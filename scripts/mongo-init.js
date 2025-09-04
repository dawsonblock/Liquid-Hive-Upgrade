// MongoDB Initialization Script for Liquid-Hive-Upgrade
// Creates databases, users, and indexes for optimal performance

// Switch to the application database
db = db.getSiblingDB('liquid_hive');

// Create application user with read/write permissions
db.createUser({
  user: 'app_user',
  pwd: 'app_password',
  roles: [
    {
      role: 'readWrite',
      db: 'liquid_hive'
    }
  ]
});

// Create collections with optimal settings
db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['id', 'created_at'],
      properties: {
        id: { bsonType: 'string' },
        email: { bsonType: 'string' },
        created_at: { bsonType: 'date' },
        updated_at: { bsonType: 'date' }
      }
    }
  }
});

db.createCollection('sessions', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['id', 'user_id', 'created_at'],
      properties: {
        id: { bsonType: 'string' },
        user_id: { bsonType: 'string' },
        created_at: { bsonType: 'date' },
        expires_at: { bsonType: 'date' }
      }
    }
  }
});

db.createCollection('tasks', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['id', 'status', 'created_at'],
      properties: {
        id: { bsonType: 'string' },
        status: { bsonType: 'string' },
        created_at: { bsonType: 'date' },
        updated_at: { bsonType: 'date' }
      }
    }
  }
});

db.createCollection('arena_evaluations', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['id', 'model_a', 'model_b', 'created_at'],
      properties: {
        id: { bsonType: 'string' },
        model_a: { bsonType: 'string' },
        model_b: { bsonType: 'string' },
        winner: { bsonType: 'string' },
        created_at: { bsonType: 'date' }
      }
    }
  }
});

// Create indexes for optimal query performance
print('Creating indexes...');

// Users collection indexes
db.users.createIndex({ 'id': 1 }, { unique: true });
db.users.createIndex({ 'email': 1 }, { unique: true, sparse: true });
db.users.createIndex({ 'created_at': -1 });

// Sessions collection indexes
db.sessions.createIndex({ 'id': 1 }, { unique: true });
db.sessions.createIndex({ 'user_id': 1 });
db.sessions.createIndex({ 'expires_at': 1 }, { expireAfterSeconds: 0 }); // TTL index

// Tasks collection indexes
db.tasks.createIndex({ 'id': 1 }, { unique: true });
db.tasks.createIndex({ 'status': 1 });
db.tasks.createIndex({ 'created_at': -1 });
db.tasks.createIndex({ 'user_id': 1, 'status': 1 });

// Arena evaluations indexes
db.arena_evaluations.createIndex({ 'id': 1 }, { unique: true });
db.arena_evaluations.createIndex({ 'model_a': 1, 'model_b': 1 });
db.arena_evaluations.createIndex({ 'created_at': -1 });
db.arena_evaluations.createIndex({ 'winner': 1 });

// Create compound indexes for common queries
db.tasks.createIndex({ 'user_id': 1, 'created_at': -1 });
db.arena_evaluations.createIndex({ 'model_a': 1, 'created_at': -1 });
db.arena_evaluations.createIndex({ 'model_b': 1, 'created_at': -1 });

print('Database initialization completed successfully!');
print('Created collections: users, sessions, tasks, arena_evaluations');
print('Created user: app_user');
print('Created optimized indexes for all collections');