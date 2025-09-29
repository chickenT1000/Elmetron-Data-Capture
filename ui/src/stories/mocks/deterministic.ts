export const FIXED_NOW_ISO = '2024-08-01T15:00:00.000Z';

export const FIXED_NOW = new Date(FIXED_NOW_ISO);

export const toDeterministicIso = (offsetMs = 0): string =>
  new Date(FIXED_NOW.getTime() + offsetMs).toISOString();
