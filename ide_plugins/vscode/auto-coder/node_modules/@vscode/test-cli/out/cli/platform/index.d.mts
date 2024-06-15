import { TestConfiguration } from '../../config.cjs';
import { CliArgs } from '../args.mjs';
import { ResolvedTestConfiguration } from '../config.mjs';
export interface IPrepareContext {
    args: CliArgs;
    config: ResolvedTestConfiguration;
    test: TestConfiguration;
}
export interface IPlatform {
    /**
     * Prepares for a test run. This is called once for any CLI invokation, and
     * the resulting `run()` may be called multiple times e.g. in a watch scenario.
     */
    prepare(context: IPrepareContext): Promise<IPreparedRun | undefined>;
}
export interface IRunContext {
    /**
     * Defined to the path where coverage should be written, if requested
     * for a test run.
     */
    coverage?: string;
}
export interface IPreparedRun {
    /** Executes the run, returning the exit code (non-zero indicates failure) */
    run(context: IRunContext): Promise<number>;
    /** Dumps the prepared configuration as a JSON object for introspection. */
    dumpJson(): object;
}
export declare const platforms: IPlatform[];
