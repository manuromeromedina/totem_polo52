import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ChatbotComponent } from './chat/chat.component';
import { LoginComponent } from './auth/login/login.component';
import { RegisterComponent } from './auth/register/register.component';
import { ResetPasswordComponent } from './auth/login/password-reset/password-reset.component';

export const routes: Routes = [
  { path: 'chat', component: ChatbotComponent },      // Ruta para el chat
  { path: 'login', component: LoginComponent },    // Ruta para el inicio de sesión
  { path: 'register', component: RegisterComponent },  
  { path: 'password-reset', component: ResetPasswordComponent }, 
  {
  path: 'empresas',
  loadComponent: () => import('./admin-polo/empresas/empresas.component').then(m => m.EmpresasComponent)
},
{
  path: 'me',
  loadComponent: () => import('./admin-empresa/admin-empresa.component').then(m => m.EmpresaMeComponent)
},
 // Ruta para el inicio de sesión

  { path: '', redirectTo: '/login', pathMatch: 'full' } // Ruta por defecto (opcional)
];