function requireRecord(value: unknown, schemaName: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`${schemaName}: expected JSON object`);
  }
  return value as Record<string, unknown>;
}

function requireOptionalRecord(value: unknown, field: string): void {
  if (value === undefined || value === null) return;
  if (typeof value !== "object" || Array.isArray(value)) throw new Error(`${field}: expected object or null`);
}

function requireRecordArray(value: unknown, field: string): Array<Record<string, unknown>> {
  if (value === undefined) return [];
  if (!Array.isArray(value)) throw new Error(`${field}: expected array`);
  return value.map((item, index) => requireRecord(item, `${field}[${index}]`));
}

function requireString(value: unknown, field: string): void {
  if (typeof value !== "string") throw new Error(`${field}: expected string`);
}

function requireNumber(value: unknown, field: string): void {
  if (typeof value !== "number") throw new Error(`${field}: expected number`);
}

export { requireNumber, requireOptionalRecord, requireRecord, requireRecordArray, requireString };
