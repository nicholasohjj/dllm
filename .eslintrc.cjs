module.exports = {
  env: {
    es2022: true,
    node: true,
  },
  extends: ['eslint:recommended'],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  ignorePatterns: [
    'node_modules/',
    '**/*.zip',
    'esp32-camera/',
    'arduino/',
    'pitch_deck/',
    'report/',
  ],
  rules: {
    'no-console': 'off',
  },
};

