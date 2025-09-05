/**
 * Centralized configuration management for Liquid Hive Dashboard.
 */

export interface DatabaseConfig {
  url: string;
  echo: boolean;
  poolSize: number;
  maxOverflow: number;
  poolTimeout: number;
  poolRecycle: number;
}

export interface RedisConfig {
  url: string;
  maxConnections: number;
  socketTimeout: number;
  socketConnectTimeout: number;
  retryOnTimeout: boolean;
}

export interface APIConfig {
  host: string;
  port: number;
  workers: number;
  reload: boolean;
  logLevel: string;
  corsOrigins: string[];
}

export interface SecurityConfig {
  secretKey: string;
  accessTokenExpireMinutes: number;
  refreshTokenExpireDays: number;
  algorithm: string;
  passwordMinLength: number;
  maxLoginAttempts: number;
  lockoutDurationMinutes: number;
}

export interface LoggingConfig {
  level: string;
  format: string;
  handlers: Array<{
    type: string;
    filename?: string;
    maxBytes?: number;
    backupCount?: number;
  }>;
}

export interface MonitoringConfig {
  metricsEnabled: boolean;
  healthCheckInterval: number;
  prometheusPort: number;
}

export interface FeaturesConfig {
  ragEnabled: boolean;
  agentAutonomy: boolean;
  swarmProtocol: boolean;
  safetyChecks: boolean;
  confidenceModeling: boolean;
  debugMode: boolean;
  mockExternalServices: boolean;
}

export interface AppConfig {
  name: string;
  version: string;
  debug: boolean;
  environment: 'development' | 'staging' | 'production' | 'test';
  database: DatabaseConfig;
  redis: RedisConfig;
  api: APIConfig;
  security: SecurityConfig;
  logging: LoggingConfig;
  monitoring: MonitoringConfig;
  features: FeaturesConfig;
}

// Base configuration
const baseConfig: Partial<AppConfig> = {
  name: 'Liquid Hive',
  version: '1.0.0',
  debug: false,
  environment: 'production',
  api: {
    host: '0.0.0.0',
    port: 8000,
    workers: 1,
    reload: false,
    logLevel: 'info',
    corsOrigins: ['http://localhost:3000', 'http://localhost:5173'],
  },
  database: {
    url: 'sqlite:///./liquid_hive.db',
    echo: false,
    poolSize: 5,
    maxOverflow: 10,
    poolTimeout: 30,
    poolRecycle: 3600,
  },
  redis: {
    url: 'redis://localhost:6379/0',
    maxConnections: 10,
    socketTimeout: 5,
    socketConnectTimeout: 5,
    retryOnTimeout: true,
  },
  security: {
    secretKey: 'change-me-in-production',
    accessTokenExpireMinutes: 30,
    refreshTokenExpireDays: 7,
    algorithm: 'HS256',
    passwordMinLength: 8,
    maxLoginAttempts: 5,
    lockoutDurationMinutes: 15,
  },
  logging: {
    level: 'INFO',
    format: 'json',
    handlers: [
      { type: 'console' },
      {
        type: 'file',
        filename: 'logs/liquid_hive.log',
        maxBytes: 10485760,
        backupCount: 5,
      },
    ],
  },
  monitoring: {
    metricsEnabled: true,
    healthCheckInterval: 30,
    prometheusPort: 9090,
  },
  features: {
    ragEnabled: true,
    agentAutonomy: true,
    swarmProtocol: true,
    safetyChecks: true,
    confidenceModeling: true,
    debugMode: false,
    mockExternalServices: false,
  },
};

// Environment-specific overrides
const environmentConfigs: Record<string, Partial<AppConfig>> = {
  development: {
    debug: true,
    environment: 'development',
    api: {
      reload: true,
      logLevel: 'debug',
    },
    database: {
      echo: true,
      url: 'sqlite:///./dev_liquid_hive.db',
    },
    logging: {
      level: 'DEBUG',
      format: 'text',
    },
    security: {
      secretKey: 'dev-secret-key-not-for-production',
      accessTokenExpireMinutes: 1440, // 24 hours for dev
    },
    features: {
      debugMode: true,
      mockExternalServices: true,
    },
  },
  production: {
    debug: false,
    environment: 'production',
    api: {
      workers: 4,
      reload: false,
      logLevel: 'warning',
    },
    database: {
      echo: false,
      poolSize: 20,
      maxOverflow: 30,
    },
    redis: {
      maxConnections: 50,
    },
    logging: {
      level: 'WARNING',
      format: 'json',
    },
    monitoring: {
      metricsEnabled: true,
      healthCheckInterval: 10,
    },
    security: {
      accessTokenExpireMinutes: 15,
      refreshTokenExpireDays: 1,
      passwordMinLength: 12,
      maxLoginAttempts: 3,
      lockoutDurationMinutes: 30,
    },
    features: {
      debugMode: false,
      mockExternalServices: false,
    },
  },
  test: {
    debug: true,
    environment: 'test',
    api: {
      port: 8001,
      logLevel: 'debug',
    },
    database: {
      url: 'sqlite:///:memory:',
      echo: false,
    },
    redis: {
      url: 'redis://localhost:6379/1',
    },
    logging: {
      level: 'DEBUG',
      format: 'text',
    },
    features: {
      debugMode: true,
      mockExternalServices: true,
    },
  },
};

/**
 * Deep merge two objects, with the second object taking precedence.
 */
function deepMerge<T extends Record<string, any>>(target: T, source: Partial<T>): T {
  const result = { ...target };
  
  for (const key in source) {
    if (source[key] !== undefined) {
      if (
        typeof source[key] === 'object' &&
        source[key] !== null &&
        !Array.isArray(source[key]) &&
        typeof result[key] === 'object' &&
        result[key] !== null &&
        !Array.isArray(result[key])
      ) {
        result[key] = deepMerge(result[key], source[key] as any);
      } else {
        result[key] = source[key] as any;
      }
    }
  }
  
  return result;
}

/**
 * Load configuration based on environment.
 */
export function loadConfig(environment?: string): AppConfig {
  const env = environment || process.env.APP_ENV || 'production';
  const envConfig = environmentConfigs[env] || {};
  
  // Merge base config with environment-specific config
  const mergedConfig = deepMerge(baseConfig, envConfig);
  
  // Override with environment variables
  const finalConfig = {
    ...mergedConfig,
    api: {
      ...mergedConfig.api,
      host: process.env.API_HOST || mergedConfig.api!.host,
      port: parseInt(process.env.API_PORT || mergedConfig.api!.port.toString()),
      workers: parseInt(process.env.API_WORKERS || mergedConfig.api!.workers.toString()),
      reload: process.env.API_RELOAD === 'true' || mergedConfig.api!.reload,
      logLevel: process.env.API_LOG_LEVEL || mergedConfig.api!.logLevel,
    },
    database: {
      ...mergedConfig.database,
      url: process.env.DATABASE_URL || mergedConfig.database!.url,
      echo: process.env.DATABASE_ECHO === 'true' || mergedConfig.database!.echo,
    },
    redis: {
      ...mergedConfig.redis,
      url: process.env.REDIS_URL || mergedConfig.redis!.url,
    },
    security: {
      ...mergedConfig.security,
      secretKey: process.env.SECRET_KEY || mergedConfig.security!.secretKey,
    },
  } as AppConfig;
  
  return finalConfig;
}

// Export default configuration
export const config = loadConfig();
export default config;