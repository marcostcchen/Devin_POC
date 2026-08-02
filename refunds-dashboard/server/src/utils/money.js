/** Rounds to cents so repeated float math never leaks fractions of a cent. */
export function roundToCents(amount) {
  return Math.round(amount * 100) / 100;
}
