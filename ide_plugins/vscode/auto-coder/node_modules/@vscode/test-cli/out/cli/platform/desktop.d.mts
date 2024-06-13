import { IPlatform, IPrepareContext, IPreparedRun } from './index.mjs';
export declare class DesktopPlatform implements IPlatform {
    /** @inheritdoc */
    prepare({ args, config, test: _test, }: IPrepareContext): Promise<IPreparedRun | undefined>;
}
