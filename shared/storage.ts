// Local encrypted storage via op-sqlite with SQLCipher
// Falls back to in-memory key-value store when op-sqlite is unavailable
// (e.g., Expo web export)

import { EnergyBattery, energyEnvelope } from './domain';

interface CacheEntry {
  key: string;
  value: string;
  updatedAt: number;
}

let db: any = null;
let kv: Map<string, string> = new Map();

async function getDb(): Promise<any> {
  if (db) return db;
  try {
    const { open } = await import('@op-engineering/op-sqlite');
    db = await open({
      name: 'neuros',
      encryptionKey: 'neuros-local-key-2026', // SQLCipher key
    });
    await db.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, updatedAt INTEGER)');
    return db;
  } catch {
    // Fallback: in-memory KV store (web export / no native)
    return null;
  }
}

export async function saveLocal(key: string, value: string): Promise<void> {
  const d = await getDb();
  if (d) {
    await d.execute(
      'INSERT OR REPLACE INTO cache (key, value, updatedAt) VALUES (?, ?, ?)',
      [key, value, Date.now()]
    );
  } else {
    kv.set(key, value);
  }
}

export async function loadLocal(key: string): Promise<string | null> {
  const d = await getDb();
  if (d) {
    const rows: any[] = await d.execute('SELECT value FROM cache WHERE key = ?', [key]);
    return rows?.[0]?.value ?? null;
  }
  return kv.get(key) ?? null;
}

export async function clearLocal(): Promise<void> {
  const d = await getDb();
  if (d) {
    await d.execute('DELETE FROM cache');
  }
  kv.clear();
}

// Convenience: cache the full state response
export async function cacheState(state: any): Promise<void> {
  await saveLocal('energy_state', JSON.stringify(state));
}

export async function getCachedState(): Promise<any> {
  const raw = await loadLocal('energy_state');
  return raw ? JSON.parse(raw) : null;
}
