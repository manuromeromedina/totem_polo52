import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class AuthenticationService {
  private usersKey = 'users';
  private sessionKey = 'sessionToken';

  constructor() {}

  register(username: string, email: string, password: string): boolean {
    const users = this.getUsers();
    if (users.find(user => user.username === username)) {
      return false; // User already exists
    }
    users.push({ username, email, password });
    localStorage.setItem(this.usersKey, JSON.stringify(users));
    return true;
  }

  login(username: string, password: string, keepLoggedIn: boolean): boolean {
    const users = this.getUsers();
    const user = users.find(u => u.username === username && u.password === password);
    if (user) {
      const token = 'mock-token-' + Math.random().toString(36).substr(2);
      if (keepLoggedIn) {
        localStorage.setItem(this.sessionKey, token);
      } else {
        sessionStorage.setItem(this.sessionKey, token);
      }
      return true;
    }
    return false;
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem(this.sessionKey) || !!sessionStorage.getItem(this.sessionKey);
  }

  logout(): void {
    localStorage.removeItem(this.sessionKey);
    sessionStorage.removeItem(this.sessionKey);
  }

  recoverPassword(email: string): string {
    const users = this.getUsers();
    const user = users.find(u => u.email === email);
    return user ? `Se ha enviado un enlace de recuperación a ${email}` : 'Email no encontrado';
  }

  private getUsers(): any[] {
    const users = localStorage.getItem(this.usersKey);
    return users ? JSON.parse(users) : [];
  }
}