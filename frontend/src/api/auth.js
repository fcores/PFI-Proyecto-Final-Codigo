import { postJson } from "./client";

export async function login(username, password) {
  return postJson("/auth/login", { username, password });
}

export async function logout() {
  return postJson("/auth/logout", {});
}
