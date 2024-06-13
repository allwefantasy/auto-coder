import { glob } from 'glob';
import { minimatch } from 'minimatch';
import { dirname, isAbsolute, join } from 'path';
import { args } from '../bin.mjs';
/** Gathers test files that match the config */
export async function gatherFiles(path, config) {
    const fileListsProms = [];
    const cwd = dirname(path);
    const ignoreGlobs = args.ignore?.map(String).filter((p) => !isAbsolute(p));
    for (const file of config.files instanceof Array ? config.files : [config.files]) {
        if (isAbsolute(file)) {
            if (!ignoreGlobs?.some((i) => minimatch(file, i))) {
                fileListsProms.push([file]);
            }
        }
        else {
            fileListsProms.push(glob(file, { cwd, ignore: ignoreGlobs }).then((l) => l.map((f) => join(cwd, f))));
        }
    }
    const files = new Set((await Promise.all(fileListsProms)).flat());
    args.ignore?.forEach((i) => files.delete(i));
    return [...files];
}
