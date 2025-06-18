// admin-polo-sidebar.component.ts
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

interface MenuItem {
  label: string;
  icon: string;
  route?: string;
  children?: MenuItem[];
  expanded?: boolean;
}

@Component({
  selector: 'app-admin-polo-sidebar',
  templateUrl: './admin-polo-sidebar.component.html',
  styleUrls: ['./admin-polo-sidebar.component.scss']
})
export class AdminPoloSidebarComponent implements OnInit {
  
  menuItems: MenuItem[] = [
    {
      label: 'Dashboard',
      icon: 'dashboard',
      route: '/admin-polo/dashboard'
    },
    {
      label: 'Gestión de Usuarios',
      icon: 'people',
      expanded: false,
      children: [
        {
          label: 'Ver Usuarios',
          icon: 'person',
          route: '/admin-polo/usuarios'
        },
        {
          label: 'Crear Usuario',
          icon: 'person_add',
          route: '/admin-polo/usuarios/crear'
        },
        {
          label: 'Roles',
          icon: 'admin_panel_settings',
          route: '/admin-polo/roles'
        }
      ]
    },
    {
      label: 'Gestión de Empresas',
      icon: 'business',
      expanded: false,
      children: [
        {
          label: 'Ver Empresas',
          icon: 'domain',
          route: '/admin-polo/empresas'
        },
        {
          label: 'Crear Empresa',
          icon: 'add_business',
          route: '/admin-polo/empresas/crear'
        }
      ]
    },
    {
      label: 'Servicios del Polo',
      icon: 'miscellaneous_services',
      expanded: false,
      children: [
        {
          label: 'Ver Servicios',
          icon: 'list_alt',
          route: '/admin-polo/servicios-polo'
        },
        {
          label: 'Crear Servicio',
          icon: 'add_circle',
          route: '/admin-polo/servicios-polo/crear'
        }
      ]
    },
    {
      label: 'Gestión de Lotes',
      icon: 'map',
      expanded: false,
      children: [
        {
          label: 'Ver Lotes',
          icon: 'terrain',
          route: '/admin-polo/lotes'
        },
        {
          label: 'Crear Lote',
          icon: 'add_location',
          route: '/admin-polo/lotes/crear'
        }
      ]
    },
    {
      label: 'Reportes',
      icon: 'analytics',
      route: '/admin-polo/reportes'
    },
    {
      label: 'Configuración',
      icon: 'settings',
      route: '/admin-polo/configuracion'
    }
  ];

  currentUser = {
    name: 'Admin Polo',
    email: 'admin@polo.com'
  };

  constructor(private router: Router) { }

  ngOnInit(): void {
    // Aquí podrías cargar los datos del usuario actual
  }

  toggleSubmenu(item: MenuItem): void {
    if (item.children) {
      item.expanded = !item.expanded;
    }
  }

  navigate(route: string): void {
    if (route) {
      this.router.navigate([route]);
    }
  }

  logout(): void {
    // Implementar lógica de logout
    console.log('Logout');
    this.router.navigate(['/login']);
  }
}