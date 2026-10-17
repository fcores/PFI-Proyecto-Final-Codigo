import { postJson } from "./client";

export async function login(username, password) {
  return postJson("/auth/login", { username, password });
}

export async function logout() {
  return postJson("/auth/logout", {});
}

export async function deleteOwnAccount(password) {
  return postJson("/users/me/baja", { password });
}

export async function changePassword(currentPassword, newPassword) {
  return postJson("/auth/password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}
