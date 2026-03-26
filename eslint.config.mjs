export default [
  {
    files: ["static/js/*.js"],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: "script",
      globals: {
        window: "readonly",
        document: "readonly",
        navigator: "readonly",
        console: "readonly",
        fetch: "readonly",
        FormData: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",  // ← ajout
        marked: "readonly"
      }
    },
    rules: {
      "no-unused-vars": "warn",
      "no-undef": "warn",
      "eqeqeq": "error",
      "no-console": "off",
      "semi": ["error", "always"],
      "quotes": ["warn", "single"],
      "no-var": "error",
      "prefer-const": "warn"
    }
  }
];