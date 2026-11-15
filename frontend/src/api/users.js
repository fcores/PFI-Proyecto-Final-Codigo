import { get, postJson, putJson } from "./client";

export async function fetchUsers() {
  const data = await get("/users");
  return data.users ?? [];
}

export async function createUser(body) {
  return postJson("/users", body);
}

export async function updateUser(userId, body) {
  return putJson(`/users/${userId}`, body);
}

export async function resetUserPassword(userId, password) {
  return postJson(`/users/${userId}/password`, { password });
}
