// Commitlint configuration
// See https://commitlint.js.org/

module.exports = {
  extends: ["@commitlint/config-conventional"],

  // Rules: [level, applicability, value]
  // level: 0 = disabled, 1 = warning, 2 = error
  // applicability: 'always' | 'never'
  rules: {
    // Type must be one of the conventional types
    "type-enum": [
      2,
      "always",
      [
        "feat", // New feature
        "fix", // Bug fix
        "docs", // Documentation only
        "style", // Code style (formatting, semicolons, etc.)
        "refactor", // Code change that neither fixes a bug nor adds a feature
        "perf", // Performance improvement
        "test", // Adding or correcting tests
        "build", // Changes to build system or dependencies
        "ci", // CI configuration changes
        "chore", // Other changes that don't modify src or test files
        "revert", // Reverts a previous commit
      ],
    ],

    // Type must be lowercase
    "type-case": [2, "always", "lower-case"],

    // Type cannot be empty
    "type-empty": [2, "never"],

    // Scope is optional but must be lowercase if provided
    "scope-case": [2, "always", "lower-case"],

    // Subject (description) rules
    "subject-case": [0], // Disable case enforcement for flexibility
    "subject-empty": [2, "never"],
    "subject-full-stop": [2, "never", "."],

    // Header (type(scope): subject) max length
    "header-max-length": [2, "always", 100],

    // Body rules
    "body-leading-blank": [2, "always"],
    "body-max-line-length": [2, "always", 200],

    // Footer rules
    "footer-leading-blank": [2, "always"],
    "footer-max-line-length": [2, "always", 200],
  },

  // Help URL shown on validation failure
  helpUrl: "https://www.conventionalcommits.org/",
};
