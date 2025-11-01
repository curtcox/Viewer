module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
  },
  extends: ["eslint:recommended"],
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "script",
  },
  globals: {
    ace: "readonly",
  },
  rules: {
    "no-unused-vars": ["error", { "args": "none", "ignoreRestSiblings": true }],
  },
};
