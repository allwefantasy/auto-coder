import { IConfigurationWithGlobalOptions, ICoverageConfiguration, TestConfiguration } from '../config.cjs';
/** Loads the default config based on the process working directory. */
export declare function loadDefaultConfigFile(): Promise<ResolvedTestConfiguration>;
/** Loads a specific config file by the path, throwing if loading fails. */
export declare function tryLoadConfigFile(path: string): Promise<ResolvedTestConfiguration>;
export declare class ResolvedTestConfiguration implements IConfigurationWithGlobalOptions {
    readonly path: string;
    readonly tests: TestConfiguration[];
    readonly coverage: ICoverageConfiguration | undefined;
    /** Directory name the configuration file resides in. */
    readonly dir: string;
    static load(config: IConfigurationWithGlobalOptions, path: string): Promise<ResolvedTestConfiguration>;
    protected constructor(config: IConfigurationWithGlobalOptions, path: string);
    /**
     * Gets the resolved extension development path for the test configuration.
     */
    extensionDevelopmentPath(test: TestConfiguration): string[];
}
