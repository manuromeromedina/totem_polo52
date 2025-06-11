import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ChatbotComponent } from './chat/chat.component';
import { LoginComponent } from './auth/login/login.component';

export const routes: Routes = [
  { path: 'chat', component: ChatbotComponent },      // Ruta para el chat
  { path: 'login', component: LoginComponent },    // Ruta para el inicio de sesión
  { path: '', redirectTo: '/login', pathMatch: 'full' } // Ruta por defecto (opcional)
];