/** @type {import('jest').Config} */
const config = {
  testEnvironment: 'jsdom',
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', { tsconfig: '<rootDir>/tsconfig.json' }],
    '^.+\\.(js|jsx)$': 'babel-jest',
  },
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  moduleNameMapper: {
  '\\.(css|less|scss)$': 'identity-obj-proxy',
  '^react-markdown$': '<rootDir>/src/test/__mocks__/react-markdown.tsx',
  '^react-syntax-highlighter$': '<rootDir>/src/test/__mocks__/react-syntax-highlighter.tsx',
  '^react-syntax-highlighter/dist/esm/styles/prism$': '<rootDir>/src/test/__mocks__/syntax-styles.ts'
  },
  modulePathIgnorePatterns: [
    '<rootDir>/src/test/__mocks__/react-markdown.js',
    '<rootDir>/src/test/__mocks__/react-syntax-highlighter.js',
    '<rootDir>/src/test/__mocks__/syntax-styles.js'
  ],
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  roots: ['<rootDir>/src'],
  testMatch: ['**/?(*.)+(test|spec).+(ts|tsx)'],
};

export default config;