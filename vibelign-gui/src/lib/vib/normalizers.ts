// === ANCHOR: NORMALIZERS_START ===
// === ANCHOR: NORMALIZERS_REQUIRERECORD_START ===
function requireRecord(value: unknown, schemaName: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`${schemaName}: expected JSON object`);
  }
  return value as Record<string, unknown>;
}
// === ANCHOR: NORMALIZERS_REQUIRERECORD_END ===

// === ANCHOR: NORMALIZERS_REQUIREOPTIONALRECORD_START ===
function requireOptionalRecord(value: unknown, field: string): void {
  if (value === undefined || value === null) return;
  if (typeof value !== "object" || Array.isArray(value)) throw new Error(`${field}: expected object or null`);
}
// === ANCHOR: NORMALIZERS_REQUIREOPTIONALRECORD_END ===

// === ANCHOR: NORMALIZERS_REQUIRERECORDARRAY_START ===
function requireRecordArray(value: unknown, field: string): Array<Record<string, unknown>> {
  if (value === undefined) return [];
  if (!Array.isArray(value)) throw new Error(`${field}: expected array`);
  return value.map((item, index) => requireRecord(item, `${field}[${index}]`));
}
// === ANCHOR: NORMALIZERS_REQUIRERECORDARRAY_END ===

// === ANCHOR: NORMALIZERS_REQUIRESTRING_START ===
function requireString(value: unknown, field: string): void {
  if (typeof value !== "string") throw new Error(`${field}: expected string`);
}
// === ANCHOR: NORMALIZERS_REQUIRESTRING_END ===

// === ANCHOR: NORMALIZERS_REQUIRENUMBER_START ===
function requireNumber(value: unknown, field: string): void {
  if (typeof value !== "number") throw new Error(`${field}: expected number`);
}
// === ANCHOR: NORMALIZERS_REQUIRENUMBER_END ===

export { requireNumber, requireOptionalRecord, requireRecord, requireRecordArray, requireString };
// === ANCHOR: NORMALIZERS_END ===
