import { get, postJson } from "./client";

export async function login(username, password) {
  return postJson("/auth/login", { username, password });
}

export async function fetchMe() {
  return get("/auth/me");
}

export async function logout() {
  return postJson("/auth/logout", {});
}
