#!/usr/bin/env node
/*---------------------------------------------------------
 * Copyright (C) Microsoft Corporation. All rights reserved.
 *--------------------------------------------------------*/
import * as chokidar from 'chokidar';
import { resolve } from 'path';
import { cliArgs, configFileDefault } from './cli/args.mjs';
import { loadDefaultConfigFile, tryLoadConfigFile, } from './cli/config.mjs';
import { Coverage } from './cli/coverage.mjs';
import { platforms } from './cli/platform/index.mjs';
export const args = cliArgs.parseSync();
class CliExpectedError extends Error {
}
main();
async function main() {
    let code = 0;
    try {
        const config = args.config !== configFileDefault
            ? await tryLoadConfigFile(resolve(process.cwd(), args.config))
            : await loadDefaultConfigFile();
        const enabledTests = new Set(args.label?.length
            ? args.label.map((label) => {
                const found = config.tests.find((c, i) => typeof label === 'string' ? c.label === label : i === label);
                if (!found) {
                    throw new CliExpectedError(`Could not find a configuration with label "${label}"`);
                }
                return found;
            })
            : new Set(config.tests));
        if (args.watch) {
            await watchConfigs(config, enabledTests);
        }
        else {
            code = await runConfigs(config, enabledTests);
        }
    }
    catch (e) {
        code = 1;
        if (e instanceof CliExpectedError) {
            console.error(e.message);
        }
        else {
            console.error(e.stack || e);
        }
    }
    finally {
        process.exit(code);
    }
}
async function prepareConfigs(config, enabledTests) {
    return await Promise.all([...enabledTests].map(async (test, i) => {
        for (const platform of platforms) {
            const p = await platform.prepare({ args, config, test });
            if (p) {
                return p;
            }
        }
        throw new CliExpectedError(`Could not find a runner for test configuration ${test.label || i}`);
    }));
}
const WATCH_RUN_DEBOUNCE = 500;
async function watchConfigs(config, enabledTests) {
    let debounceRun;
    let rerun = false;
    let running = true;
    let prepared;
    const runOrDebounce = () => {
        if (debounceRun) {
            clearTimeout(debounceRun);
        }
        debounceRun = setTimeout(async () => {
            running = true;
            rerun = false;
            try {
                prepared ??= await prepareConfigs(config, enabledTests);
                await runPreparedConfigs(config, prepared);
            }
            finally {
                running = false;
                if (rerun) {
                    runOrDebounce();
                }
            }
        }, WATCH_RUN_DEBOUNCE);
    };
    const watcher = chokidar.watch(args.watchFiles?.length ? args.watchFiles.map(String) : process.cwd(), {
        ignored: [
            '**/.vscode-test/**',
            '**/node_modules/**',
            ...(args.watchIgnore || []).map(String),
        ],
        ignoreInitial: true,
    });
    watcher.on('all', (evts) => {
        if (evts !== 'change') {
            prepared = undefined; // invalidate since files will need to be re-scanned
        }
        if (running) {
            rerun = true;
        }
        else {
            runOrDebounce();
        }
    });
    watcher.on('ready', () => {
        runOrDebounce();
    });
    // wait until interrupted
    await new Promise(() => {
        /* no-op */
    });
}
async function runPreparedConfigs(config, prepared) {
    const coverage = args.coverage ? new Coverage(config, args) : undefined;
    const context = { coverage: coverage?.targetDir };
    let code = 0;
    for (const p of prepared) {
        code = Math.max(code, await p.run(context));
        if (args.bail && code !== 0) {
            return code;
        }
    }
    await coverage?.write();
    return code;
}
/** Runs the given test configurations. */
async function runConfigs(config, enabledTests) {
    const prepared = await prepareConfigs(config, enabledTests);
    if (args.listConfiguration) {
        await new Promise((r) => process.stdout.write(JSON.stringify(prepared.map((p) => p.dumpJson())), r));
        return 0;
    }
    return runPreparedConfigs(config, prepared);
}
