export declare const ensureArray: <T>(value: T | T[]) => T[];
export declare const readJSON: <T>(path: string) => Promise<T>;
export declare const writeJSON: (path: string, value: unknown) => Promise<void>;
/**
 * Applies the "replacer" function to primitive keys and properties of the object,
 * mutating it in-place.
 */
export declare const mutateObjectPrimitives: (obj: any, replacer: (value: any) => any) => any;
