/*---------------------------------------------------------
 * Copyright (C) Microsoft Corporation. All rights reserved.
 *--------------------------------------------------------*/
import { promises as fs } from 'fs';
export const ensureArray = (value) => (Array.isArray(value) ? value : [value]);
export const readJSON = async (path) => JSON.parse(await fs.readFile(path, 'utf8'));
export const writeJSON = async (path, value) => fs.writeFile(path, JSON.stringify(value));
/**
 * Applies the "replacer" function to primitive keys and properties of the object,
 * mutating it in-place.
 */
export const mutateObjectPrimitives = (obj, replacer) => {
    if (Array.isArray(obj)) {
        for (let i = 0; i < obj.length; i++) {
            obj[i] = mutateObjectPrimitives(obj[i], replacer);
        }
        return obj;
    }
    if (obj && typeof obj === 'object') {
        for (const [key, value] of Object.entries(obj)) {
            const newKey = replacer(key);
            if (newKey !== key) {
                delete obj[key];
            }
            obj[newKey] = mutateObjectPrimitives(value, replacer);
        }
        return obj;
    }
    return replacer(obj);
};
