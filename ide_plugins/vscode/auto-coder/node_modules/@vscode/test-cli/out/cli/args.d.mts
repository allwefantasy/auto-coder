/// <reference types="yargs" />
export declare const configFileDefault = "nearest .vscode-test.js";
export declare const cliArgs: import("yargs").Argv<{
    config: string;
} & {
    label: (string | number)[] | undefined;
} & {
    "code-version": string | undefined;
} & {
    "install-extensions": (string | number)[] | undefined;
} & {
    "skip-extension-dependencies": boolean;
} & {
    bail: boolean | undefined;
} & {
    "dry-run": boolean | undefined;
} & {
    "list-configuration": boolean | undefined;
} & {
    "fail-zero": boolean | undefined;
} & {
    "forbid-only": boolean | undefined;
} & {
    "forbid-pending": boolean | undefined;
} & {
    jobs: number;
} & {
    parallel: boolean | undefined;
} & {
    retries: number | undefined;
} & {
    slow: number;
} & {
    timeout: number;
} & {
    color: boolean | undefined;
} & {
    diff: boolean;
} & {
    "full-trace": boolean | undefined;
} & {
    "inline-diffs": boolean | undefined;
} & {
    reporter: string;
} & {
    "reporter-option": (string | number)[] | undefined;
} & {
    file: (string | number)[] | undefined;
} & {
    ignore: (string | number)[] | undefined;
} & {
    watch: boolean | undefined;
} & {
    "watch-files": (string | number)[] | undefined;
} & {
    "watch-ignore": (string | number)[] | undefined;
} & {
    run: (string | number)[] | undefined;
} & {
    fgrep: string | undefined;
} & {
    grep: string | undefined;
} & {
    invert: boolean | undefined;
} & {
    coverage: boolean | undefined;
} & {
    "coverage-output": string | undefined;
} & {
    "coverage-reporter": (string | number)[] | undefined;
}>;
export type CliArgs = ReturnType<(typeof cliArgs)['parseSync']>;
