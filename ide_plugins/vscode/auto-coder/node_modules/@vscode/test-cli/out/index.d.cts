import { IConfigurationWithGlobalOptions, TestConfiguration } from './config.cjs';
export * from './config.cjs';
export * from './fullJsonStreamReporterTypes.cjs';
type AnyConfiguration = IConfigurationWithGlobalOptions | TestConfiguration | TestConfiguration[];
type AnyConfigurationOrPromise = AnyConfiguration | Promise<AnyConfiguration>;
export declare const defineConfig: (config: AnyConfigurationOrPromise | (() => AnyConfigurationOrPromise)) => AnyConfigurationOrPromise | (() => AnyConfigurationOrPromise);
