import { cpus } from 'os';
import yargs from 'yargs';
const rulesAndBehavior = 'Mocha: Rules & Behavior';
const reportingAndOutput = 'Mocha: Reporting & Output';
const fileHandling = 'Mocha: File Handling';
const testFilters = 'Mocha: Test Filters';
const testCoverage = 'Test Coverage';
const vscodeSection = 'VS Code Options';
export const configFileDefault = 'nearest .vscode-test.js';
export const cliArgs = yargs(process.argv)
    .epilogue('See https://code.visualstudio.com/api/working-with-extensions/testing-extension for help')
    .option('config', {
    type: 'string',
    description: 'Config file to use',
    default: configFileDefault,
    group: vscodeSection,
})
    .option('label', {
    alias: 'l',
    type: 'array',
    description: 'Specify the test configuration to run based on its label in configuration',
    group: vscodeSection,
})
    .option('code-version', {
    type: 'string',
    description: 'Override the VS Code version used to run tests',
    group: vscodeSection,
})
    .option('install-extensions', {
    type: 'array',
    description: 'A list of vscode extensions to install prior to running the tests, in the same format as `code --install-extensions`',
    group: vscodeSection,
})
    .option('skip-extension-dependencies', {
    type: 'boolean',
    default: false,
    description: "Skip installing extensions' the `extensionDependencies`",
    group: vscodeSection,
})
    //#region Rules & Behavior
    .option('bail', {
    alias: 'b',
    type: 'boolean',
    description: 'Abort ("bail") after first test failure',
    group: rulesAndBehavior,
})
    .option('dry-run', {
    type: 'boolean',
    description: 'Report tests without executing them',
    group: rulesAndBehavior,
})
    .option('list-configuration', {
    type: 'boolean',
    description: 'List configurations and that they woud run, without executing them',
    group: rulesAndBehavior,
})
    .option('fail-zero', {
    type: 'boolean',
    description: 'Fail test run if no test(s) encountered',
    group: rulesAndBehavior,
})
    .option('forbid-only', {
    type: 'boolean',
    description: 'Fail if exclusive test(s) encountered',
    group: rulesAndBehavior,
})
    .option('forbid-pending', {
    type: 'boolean',
    description: 'Fail if pending test(s) encountered',
    group: rulesAndBehavior,
})
    .option('jobs', {
    alias: 'j',
    type: 'number',
    description: 'Number of concurrent jobs for --parallel; use 1 to run in serial',
    default: Math.max(1, cpus().length - 1),
    group: rulesAndBehavior,
})
    .options('parallel', {
    alias: 'p',
    type: 'boolean',
    description: 'Run tests in parallel',
    group: rulesAndBehavior,
})
    .option('retries', {
    alias: 'r',
    type: 'number',
    description: 'Number of times to retry failed tests',
    group: rulesAndBehavior,
})
    .option('slow', {
    alias: 's',
    type: 'number',
    description: 'Specify "slow" test threshold (in milliseconds)',
    default: 75,
    group: rulesAndBehavior,
})
    .option('timeout', {
    alias: 't',
    type: 'number',
    description: 'Specify test timeout threshold (in milliseconds)',
    default: 2000,
    group: rulesAndBehavior,
})
    //#endregion
    //#region Reporting & Output
    .option('color', {
    alias: 'c',
    type: 'boolean',
    description: 'Force-enable color output',
    group: reportingAndOutput,
})
    .option('diff', {
    type: 'boolean',
    description: 'Show diff on failure',
    default: true,
    group: reportingAndOutput,
})
    .option('full-trace', {
    type: 'boolean',
    description: 'Display full stack traces',
    group: reportingAndOutput,
})
    .option('inline-diffs', {
    type: 'boolean',
    description: 'Display actual/expected differences inline within each string',
    group: reportingAndOutput,
})
    .option('reporter', {
    alias: 'R',
    type: 'string',
    description: 'Specify reporter to use',
    default: 'spec',
    group: reportingAndOutput,
})
    .option('reporter-option', {
    alias: 'O',
    type: 'array',
    description: 'Reporter-specific options (<k=v,[k1=v1,..]>)',
    group: reportingAndOutput,
})
    //#endregion
    //#region File Handling
    .option('file', {
    type: 'array',
    description: 'Specify file(s) to be loaded prior to root suite',
    group: fileHandling,
})
    .option('ignore', {
    alias: 'exclude',
    type: 'array',
    description: 'Ignore file(s) or glob pattern(s)',
    group: fileHandling,
})
    .option('watch', {
    alias: 'w',
    type: 'boolean',
    description: 'Watch files in the current working directory for changes',
    group: fileHandling,
})
    .option('watch-files', {
    type: 'array',
    description: 'List of paths or globs to watch',
    group: fileHandling,
})
    .option('watch-ignore', {
    type: 'array',
    description: 'List of paths or globs to exclude from watching',
    group: fileHandling,
})
    .option('run', {
    type: 'array',
    description: 'List of specific files to run',
    group: fileHandling,
})
    //#endregion
    //#region Test Filters
    .option('fgrep', {
    type: 'string',
    alias: 'f',
    description: 'Only run tests containing this string',
    group: testFilters,
})
    .option('grep', {
    type: 'string',
    alias: 'g',
    description: 'Only run tests matching this string or regexp',
    group: testFilters,
})
    .option('invert', {
    alias: 'i',
    type: 'boolean',
    description: 'Inverts --grep and --fgrep matches',
    group: testFilters,
})
    //#endregion
    //#region Test Coverage
    .option('coverage', {
    type: 'boolean',
    description: 'Whether to run with coverage.',
    group: testCoverage,
})
    .option('coverage-output', {
    type: 'string',
    description: 'Directory where coverage data should be written.',
    group: testCoverage,
})
    .option('coverage-reporter', {
    type: 'array',
    description: 'One or more coverage reporters to use.',
    group: testCoverage,
});
//#endregion
cliArgs.wrap(Math.min(120, cliArgs.terminalWidth()));
