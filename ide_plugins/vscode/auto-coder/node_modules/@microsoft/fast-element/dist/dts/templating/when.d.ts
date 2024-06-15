import type { Binding } from "../observation/observable.js";
import type { CaptureType, SyntheticViewTemplate } from "./template.js";
/**
 * A directive that enables basic conditional rendering in a template.
 * @param binding - The condition to test for rendering.
 * @param templateOrTemplateBinding - The template or a binding that gets
 * the template to render when the condition is true.
 * @param elseTemplateOrTemplateBinding - Optional template or binding that that
 * gets the template to render when the conditional is false.
 * @public
 */
export declare function when<TSource = any, TReturn = any>(binding: Binding<TSource, TReturn>, templateOrTemplateBinding: SyntheticViewTemplate | Binding<TSource, SyntheticViewTemplate>, elseTemplateOrTemplateBinding?: SyntheticViewTemplate | Binding<TSource, SyntheticViewTemplate>): CaptureType<TSource>;
