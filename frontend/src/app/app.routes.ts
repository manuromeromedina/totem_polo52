import { Routes } from '@angular/router';
import { AuthGuard } from './auth.guard';
import { ChatbotComponent } from './chat/chat.component';
import { LoginComponent } from './auth/login/login.component';
import { RegisterComponent } from './auth/register/register.component';
import { ResetPasswordComponent } from './auth/login/password-reset/password-reset.component';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/login',
    pathMatch: 'full'
  },
  {
    path: 'login',
    component: LoginComponent
  },
  {
    path: 'register',
    component: RegisterComponent
  },
  {
    path: 'password-reset',
    component: ResetPasswordComponent
  },
  {
    path: 'chat',
    component: ChatbotComponent,
    canActivate: [AuthGuard],
    data: { role: 'publico' }
  },
  {
    path: 'empresas',
    loadComponent: () => import('./admin-polo/admin-polo.component').then(m => m.AdminPoloComponent),
    canActivate: [AuthGuard],
    data: { role: 'admin_polo' }
  },
  {
    path: 'me',
    loadComponent: () => import('./admin-empresa/admin-empresa.component').then(m => m.EmpresaMeComponent),
    canActivate: [AuthGuard],
    data: { role: 'admin_empresa' }
  },
  {
    path: '**',
    redirectTo: '/login'
  }
];