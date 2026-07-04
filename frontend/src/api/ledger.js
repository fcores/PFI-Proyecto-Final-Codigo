import { get } from "./client";

export async function fetchLedger() {
  const data = await get("/ledger");
  return data.blocks ?? [];
}

export async function verifyLedger() {
  return get("/ledger/verify");
}
