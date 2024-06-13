import resolveCb from 'enhanced-resolve';
import { promisify } from 'util';
import { CliExpectedError } from './error.mjs';
export const commonJsResolve = promisify(resolveCb);
/**
 * Resolves the module in context of the configuration.
 *
 * Only does traditional Node resolution without looking at the `exports` field
 * or alternative extensions (cjs/mjs) to match what the VS Code loader does.
 */
export const mustResolve = async (context, moduleName) => {
    const path = await commonJsResolve(context, moduleName);
    if (!path) {
        let msg = `Could not resolve module "${moduleName}" in ${path}`;
        if (!moduleName.startsWith('.')) {
            msg += ' (you may need to install with `npm install`)';
        }
        throw new CliExpectedError(msg);
    }
    return path;
};
