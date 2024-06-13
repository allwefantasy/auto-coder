import { CliArgs } from './args.mjs';
import { ResolvedTestConfiguration } from './config.mjs';
/**
 * Manages collecting coverage data from test runs. All runs, regardless of
 * platform, expect coverage data given in the V8 coverage format. We then
 * use c8 to convert it to the common Istanbul format and represent it with
 * a variety of reporters.
 */
export declare class Coverage {
    private readonly config;
    private readonly args;
    readonly targetDir: string;
    constructor(config: ResolvedTestConfiguration, args: CliArgs);
    write(): Promise<void>;
    private getSourcesDirectories;
}
