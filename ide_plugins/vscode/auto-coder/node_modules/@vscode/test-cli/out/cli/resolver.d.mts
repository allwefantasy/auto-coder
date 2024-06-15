export declare const commonJsResolve: (arg1: string, arg2: string) => Promise<string | false | undefined>;
/**
 * Resolves the module in context of the configuration.
 *
 * Only does traditional Node resolution without looking at the `exports` field
 * or alternative extensions (cjs/mjs) to match what the VS Code loader does.
 */
export declare const mustResolve: (context: string, moduleName: string) => Promise<string>;
