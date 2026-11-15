import { z } from "zod";

export const emailSchema = z
  .string()
  .trim()
  .min(1, "Enter your email address.")
  .max(320, "That email address is too long.")
  .pipe(z.email("Enter a valid email address."));

/** Validates one text field of a lesson exercise against the limits the lesson defines. */
export function textFieldSchema(minLength: number, maxLength: number) {
  return z
    .string()
    .trim()
    .min(minLength, minLength <= 1 ? "This answer is required." : `Write at least ${minLength} characters.`)
    .max(maxLength, `Keep it under ${maxLength} characters.`);
}
