/*---------------------------------------------------------
 * Copyright (C) Microsoft Corporation. All rights reserved.
 *--------------------------------------------------------*/
import { Report } from 'c8';
import { randomUUID } from 'crypto';
import { existsSync, promises as fs, mkdirSync } from 'fs';
import { tmpdir } from 'os';
import { join, resolve } from 'path';
import { CliExpectedError } from './error.mjs';
const srcDirCandidates = ['src', 'lib', '.'];
/**
 * Manages collecting coverage data from test runs. All runs, regardless of
 * platform, expect coverage data given in the V8 coverage format. We then
 * use c8 to convert it to the common Istanbul format and represent it with
 * a variety of reporters.
 */
export class Coverage {
    config;
    args;
    targetDir = join(tmpdir(), `vsc-coverage-${randomUUID()}`);
    constructor(config, args) {
        this.config = config;
        this.args = args;
        mkdirSync(this.targetDir, { recursive: true });
    }
    async write() {
        const cfg = this.config.coverage || {};
        let defaultReporters = ['text-summary', 'html'];
        let reporterOptions;
        if (Array.isArray(cfg.reporter)) {
            defaultReporters = cfg.reporter;
        }
        else if (cfg.reporter) {
            defaultReporters = Object.keys(cfg.reporter);
            reporterOptions = cfg.reporter;
        }
        try {
            const report = new Report({
                tempDirectory: this.targetDir,
                exclude: cfg.exclude,
                include: cfg.include,
                reporter: this.args.coverageReporter?.length
                    ? this.args.coverageReporter.map(String)
                    : defaultReporters,
                reporterOptions,
                reportsDirectory: this.args.coverageOutput || join(this.config.dir, 'coverage'),
                src: this.getSourcesDirectories(),
                all: cfg.includeAll,
                excludeNodeModules: true,
                // not yet in the .d.ts for c8:
                //@ts-ignore
                mergeAsync: true,
            });
            // A hacky fix due to an outstanding bug in Istanbul's exclusion testing
            // code: its subdirectory checks are case-sensitive on Windows, but file
            // URIs might have mixed casing.
            //
            // Setting `relativePath: false` on the exclude bypasses this code path.
            //
            // https://github.com/istanbuljs/test-exclude/issues/43
            // https://github.com/istanbuljs/test-exclude/blob/a5b1d07584109f5f553ccef97de64c6cbfca4764/index.js#L91
            report.exclude.relativePath = false;
            // While we're hacking, may as well keep hacking: we don't want to mess
            // with default excludes, but we want to exclude the .vscode-test internals
            report.exclude.exclude.push('**/.vscode-test/**');
            await report.run();
        }
        catch (e) {
            throw new CliExpectedError(`Coverage report generated failed, please file an issue with original reports located in ${this.targetDir}:\n\n${e}`);
        }
        await fs.rm(this.targetDir, { recursive: true, force: true });
    }
    getSourcesDirectories() {
        const srcs = new Set();
        for (const test of this.config.tests) {
            const dir = this.config.extensionDevelopmentPath(test);
            let srcDir = test.srcDir;
            for (const candidate of srcDirCandidates) {
                if (srcDir) {
                    break;
                }
                const candidatePath = resolve(dir[0], candidate);
                if (existsSync(candidatePath)) {
                    srcDir = candidatePath;
                }
            }
            if (srcDir) {
                srcs.add(srcDir);
            }
        }
        return [...srcs];
    }
}
