const js = require("@eslint/js");
const globals = require("globals");

module.exports = [
  { ignores: ["dist/", "node_modules/"] },
  js.configs.recommended,
  {
    files: ["**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: { ...globals.browser, ...globals.node },
    },
    rules: {
      "no-unused-vars": ["error", { caughtErrors: "none" }],
      eqeqeq: "error",
      "no-var": "error",
      "prefer-const": "error",
    },
  },
  {
    files: ["app.js"],
    languageOptions: {
      globals: { formatDate: "readonly", buildTaskPayload: "readonly" },
    },
  },
  {
    files: ["utils.js"],
    rules: { "no-unused-vars": "off" },
  },
];