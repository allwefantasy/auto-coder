import { TestConfiguration } from '../config.cjs';
/** Gathers test files that match the config */
export declare function gatherFiles(path: string, config: TestConfiguration): Promise<string[]>;
