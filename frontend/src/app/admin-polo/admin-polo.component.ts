import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import {
  AdminPoloService,
  Empresa,
  EmpresaCreate,
  EmpresaUpdate,
  Usuario,
  UsuarioCreate,
  UsuarioUpdate,
  Rol,
  ServicioPolo,
  ServicioPoloCreate,
  Lote,
  LoteCreate,
} from './admin-polo.service';
import { LogoutButtonComponent } from '../shared/logout-button/logout-button.component';

@Component({
  selector: 'app-empresas',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, LogoutButtonComponent],
  templateUrl: './admin-polo.component.html',
  styleUrls: ['./admin-polo.component.css'],
})
export class AdminPoloComponent implements OnInit {
  activeTab = 'empresas';

  // Empresas
  empresas: Empresa[] = [];
  showEmpresaForm = false;
  editingEmpresa: Empresa | null = null;
  empresaForm: EmpresaCreate = {
    cuil: 0,
    nombre: '',
    rubro: '',
    cant_empleados: 0,
    observaciones: '',
    horario_trabajo: '',
  };

  selectedEmpresa: Empresa | null = null;
  creatingForEmpresa = false;

  // Usuarios
  usuarios: Usuario[] = [];
  roles: Rol[] = [];
  showUsuarioForm = false;
  editingUsuario: Usuario | null = null;
  usuarioForm: UsuarioCreate = {
    email: '',
    nombre: '',
    password: '',
    estado: true,
    cuil: null as any, // Cambia de 0 a null
    id_rol: null as any, // Cambia de 0 a null
  };

  // Servicios del Polo
  serviciosPolo: ServicioPolo[] = [];
  showServicioPoloForm = false;
  servicioPoloForm: ServicioPoloCreate = {
    nombre: '',
    horario: '',
    datos: {
      cant_puestos: null,
      m2: null,
      datos_prop: {
        nombre: '',
        contacto: '',
      },
      datos_inquilino: {
        nombre: '',
        contacto: '',
      },
    },
    propietario: '',
    id_tipo_servicio_polo: 1,
    cuil: 0,
  };
  nombreServicioSeleccionado: string = '';

  // Lotes
  lotes: Lote[] = [];
  showLoteForm = false;
  loteForm: LoteCreate = {
    dueno: '',
    lote: 0,
    manzana: 0,
    id_servicio_polo: 0,
  };

  // Estados
  loading = false;
  message = '';
  messageType: 'success' | 'error' = 'success';

  constructor(private adminPoloService: AdminPoloService) {}

  public isDarkMode: boolean = false;

  ngOnInit(): void {
    this.loadRoles();
    // Cargar datos de la pestaña activa por defecto
    this.loadData();
    const savedTheme = localStorage.getItem('theme');
    this.isDarkMode = savedTheme === 'dark';
  }

  toggleDarkMode(): void {
    this.isDarkMode = !this.isDarkMode;
    localStorage.setItem('theme', this.isDarkMode ? 'dark' : 'light');
  }

  updateTheme(): void {
    const body = document.body;
    if (this.isDarkMode) {
      body.classList.add('dark-mode');
    } else {
      body.classList.remove('dark-mode');
    }
  }

  setActiveTab(tab: string): void {
    this.activeTab = tab;
    this.resetForms();
    this.loadData();
  }

  loadRoles(): void {
    this.adminPoloService.getRoles().subscribe({
      next: (roles) => {
        this.roles = roles;
      },
      error: (error) => {
        console.error('Error loading roles:', error);
      },
    });
  }

  loadData(): void {
    this.loading = true;

    switch (this.activeTab) {
      case 'empresas':
        this.loadEmpresas();
        break;
      case 'usuarios':
        this.loadUsuarios();
        break;
      case 'servicios':
        this.loadServiciosPolo();
        break;
      case 'lotes':
        this.loadLotes();
        break;
      default:
        this.loading = false;
    }
  }

  loadEmpresas(): void {
    this.adminPoloService.getEmpresas().subscribe({
      next: (empresas) => {
        this.empresas = empresas;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading empresas:', error);
        this.showMessage(
          'Error al cargar empresas: ' + (error.error?.detail || error.message),
          'error'
        );
        this.loading = false;
      },
    });
  }

  loadUsuarios(): void {
    this.adminPoloService.getUsers().subscribe({
      next: (usuarios) => {
        this.usuarios = usuarios;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading usuarios:', error);
        this.showMessage(
          'Error al cargar usuarios: ' + (error.error?.detail || error.message),
          'error'
        );
        this.loading = false;
      },
    });
  }

  loadServiciosPolo(): void {
    this.adminPoloService.getServiciosPolo().subscribe({
      next: (servicios) => {
        this.serviciosPolo = servicios;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading servicios polo:', error);
        this.showMessage(
          'Error al cargar servicios del polo: ' +
            (error.error?.detail || error.message),
          'error'
        );
        this.loading = false;
      },
    });
  }

  loadLotes(): void {
    this.adminPoloService.getLotes().subscribe({
      next: (lotes) => {
        this.lotes = lotes;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading lotes:', error);
        this.showMessage(
          'Error al cargar lotes: ' + (error.error?.detail || error.message),
          'error'
        );
        this.loading = false;
      },
    });
  }

  resetForms(): void {
    this.showEmpresaForm = false;
    this.showUsuarioForm = false;
    this.showServicioPoloForm = false;
    this.showLoteForm = false;
    this.editingEmpresa = null;
    this.editingUsuario = null;
    this.selectedEmpresa = null; // AGREGAR ESTA LÍNEA
    this.creatingForEmpresa = false; // AGREGAR ESTA LÍNEA
    this.message = '';

    this.empresaForm = {
      cuil: 0,
      nombre: '',
      rubro: '',
      cant_empleados: 0,
      observaciones: '',
      horario_trabajo: '',
    };

    this.usuarioForm = {
      email: '',
      nombre: '',
      password: '',
      estado: true,
      cuil: null as any, // Cambia de 0 a null
      id_rol: null as any,
    };

    this.servicioPoloForm = {
      nombre: '',
      horario: '',
      datos: {
        cant_puestos: null,
        m2: null,
        datos_prop: { nombre: '', contacto: '' },
        datos_inquilino: { nombre: '', contacto: '' },
      },
      propietario: '',
      id_tipo_servicio_polo: 1,
      cuil: 0,
    };

    this.loteForm = {
      dueno: '',
      lote: 0,
      manzana: 0,
      id_servicio_polo: 0,
    };
  }

  showMessage(message: string, type: 'success' | 'error'): void {
    this.message = message;
    this.messageType = type;
    setTimeout(() => {
      this.message = '';
    }, 5000);
  }

  // EMPRESAS
  openEmpresaForm(empresa?: Empresa): void {
    if (empresa) {
      this.editingEmpresa = empresa;
      this.empresaForm = { ...empresa };
    } else {
      this.editingEmpresa = null;
      this.resetForms();
    }
    this.showEmpresaForm = true;
  }

  onSubmitEmpresa(): void {
    this.loading = true;

    if (this.editingEmpresa) {
      // Actualizar
      const updateData: EmpresaUpdate = {
        nombre: this.empresaForm.nombre,
        rubro: this.empresaForm.rubro,
      };

      this.adminPoloService
        .updateEmpresa(this.editingEmpresa.cuil, updateData)
        .subscribe({
          next: (empresa) => {
            this.showMessage('Empresa actualizada exitosamente', 'success');
            this.resetForms();
            this.loadEmpresas(); // Recargar la lista específica
            this.loading = false;
          },
          error: (error) => {
            this.showMessage(
              'Error al actualizar empresa: ' +
                (error.error?.detail || error.message),
              'error'
            );
            this.loading = false;
          },
        });
    } else {
      // Crear
      this.adminPoloService.createEmpresa(this.empresaForm).subscribe({
        next: (empresa) => {
          this.showMessage('Empresa creada exitosamente', 'success');
          this.empresas.push(empresa);
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          this.showMessage(
            'Error al crear empresa: ' + (error.error?.detail || error.message),
            'error'
          );
          this.loading = false;
        },
      });
    }
  }

  deleteEmpresa(cuil: number): void {
    if (confirm('¿Está seguro de que desea eliminar esta empresa?')) {
      this.adminPoloService.deleteEmpresa(cuil).subscribe({
        next: () => {
          this.showMessage('Empresa eliminada exitosamente', 'success');
          this.loadEmpresas(); // Recargar la lista
        },
        error: (error) => {
          this.showMessage(
            'Error al eliminar empresa: ' +
              (error.error?.detail || error.message),
            'error'
          );
        },
      });
    }
  }

  // USUARIOS
  openUsuarioForm(usuario?: Usuario): void {
    if (usuario) {
      this.editingUsuario = usuario;
      this.usuarioForm = {
        email: usuario.email,
        nombre: usuario.nombre,
        password: '', // Siempre vacío para edición
        estado: usuario.estado,
        cuil: usuario.cuil,
        id_rol: 0, // Se mantendrá el rol existente
      };
    } else {
      this.editingUsuario = null;
      this.usuarioForm = {
        email: '',
        nombre: '',
        password: '',
        estado: true,
        cuil: null as any, // Cambia de 0 a null
        id_rol: null as any,
      };
    }
    this.showUsuarioForm = true;
  }

  onSubmitUsuario(): void {
    this.loading = true;

    if (this.editingUsuario) {
      // Actualizar
      const updateData: UsuarioUpdate = {
        password: this.usuarioForm.password || undefined,
        estado: this.usuarioForm.estado,
      };

      this.adminPoloService
        .updateUser(this.editingUsuario.id_usuario, updateData)
        .subscribe({
          next: (usuario) => {
            this.showMessage('Usuario actualizado exitosamente', 'success');
            this.resetForms();
            this.loadUsuarios();
            this.loading = false;
          },
          error: (error) => {
            // REEMPLAZA ESTA LÍNEA:
            let errorMessage = 'Error al actualizar usuario';

            if (error.error?.detail && Array.isArray(error.error.detail)) {
              const validationErrors = error.error.detail
                .map((err: any) => err.msg)
                .join(', ');
              errorMessage = validationErrors;
            } else if (error.error?.detail) {
              errorMessage = error.error.detail;
            } else {
              errorMessage = error.message;
            }

            this.showMessage(errorMessage, 'error');
            this.loading = false;
          },
        });
    } else {
      // Crear - validar que todos los campos requeridos estén presentes
      if (!this.usuarioForm.email) {
        this.showMessage('El email es requerido', 'error');
        this.loading = false;
        return;
      }

      if (!this.usuarioForm.nombre) {
        this.showMessage('El nombre de usuario es requerido', 'error');
        this.loading = false;
        return;
      }

      if (!this.usuarioForm.cuil || this.usuarioForm.cuil === 0) {
        this.showMessage('El CUIL de empresa es requerido', 'error');
        this.loading = false;
        return;
      }

      if (!this.usuarioForm.id_rol || this.usuarioForm.id_rol === 0) {
        this.showMessage('Debe seleccionar un rol', 'error');
        this.loading = false;
        return;
      }

      // AGREGA ESTA VALIDACIÓN DE CONTRASEÑA AQUÍ:
      const passwordError = this.validatePassword(this.usuarioForm.password);
      if (passwordError) {
        this.showMessage(passwordError, 'error');
        this.loading = false;
        return;
      }

      this.adminPoloService.createUser(this.usuarioForm).subscribe({
        next: (usuario) => {
          this.showMessage('Usuario creado exitosamente', 'success');
          this.usuarios.push(usuario);
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          console.log('Error completo:', error);
          console.log('Error detail:', error.error?.detail);

          // REEMPLAZA ESTA PARTE:
          let errorMessage = 'Error al crear usuario';

          if (error.error?.detail && Array.isArray(error.error.detail)) {
            const validationErrors = error.error.detail
              .map((err: any) => err.msg)
              .join(', ');
            errorMessage = validationErrors;
          } else if (error.error?.detail) {
            errorMessage = error.error.detail;
          } else {
            errorMessage = error.message;
          }

          this.showMessage(errorMessage, 'error');
          this.loading = false;
        },
      });
    }
  }
  toggleUsuarioEstado(usuario: Usuario): void {
    const accion = usuario.estado ? 'inhabilitar' : 'habilitar';
    const nuevoEstado = !usuario.estado;

    if (confirm(`¿Está seguro de que desea ${accion} este usuario?`)) {
      const updateData: UsuarioUpdate = {
        estado: nuevoEstado,
      };

      this.adminPoloService
        .updateUser(usuario.id_usuario, updateData)
        .subscribe({
          next: (usuarioActualizado) => {
            // Actualizar el usuario en la lista local
            const index = this.usuarios.findIndex(
              (u) => u.id_usuario === usuario.id_usuario
            );
            if (index !== -1) {
              this.usuarios[index] = usuarioActualizado;
            }

            this.showMessage(`Usuario ${accion}do exitosamente`, 'success');
          },
          error: (error) => {
            this.showMessage(
              `Error al ${accion} usuario: ` +
                (error.error?.detail || error.message),
              'error'
            );
          },
        });
    }
  }

  // SERVICIOS DEL POLO
  openServicioPoloForm(): void {
    this.showServicioPoloForm = true;
  }
  isCantPuestosRequired(): boolean {
    return this.servicioPoloForm.id_tipo_servicio_polo === 1;
  }

  isM2Required(): boolean {
    return this.servicioPoloForm.id_tipo_servicio_polo !== 1;
  }

  onSubmitServicioPolo(): void {
    const tipo = this.servicioPoloForm.id_tipo_servicio_polo;
    const datos = this.servicioPoloForm.datos || {};

    // Validaciones manuales
    if (tipo === 1 && (!datos.cant_puestos || datos.cant_puestos <= 0)) {
      this.showMessage(
        'Debe ingresar la cantidad de puestos para coworking.',
        'error'
      );
      return;
    }

    if (tipo !== 1 && (!datos.m2 || datos.m2 <= 0)) {
      this.showMessage(
        'Debe ingresar los metros cuadrados para este tipo de servicio.',
        'error'
      );
      return;
    }

    // Enviar
    this.loading = true;
    this.adminPoloService.createServicioPolo(this.servicioPoloForm).subscribe({
      next: (servicio) => {
        this.showMessage('Servicio del polo creado exitosamente', 'success');
        this.serviciosPolo.push(servicio);
        this.resetForms();
        this.loading = false;
      },
      error: (error) => {
        this.showMessage(
          'Error al crear servicio del polo: ' +
            (error.error?.detail || error.message),
          'error'
        );
        this.loading = false;
      },
    });
  }

  onTipoServicioChange(): void {
    const tipo = this.servicioPoloForm.id_tipo_servicio_polo;

    // Aseguramos estructura inicial
    if (!this.servicioPoloForm.datos) {
      this.servicioPoloForm.datos = {};
    }

    // Limpiar campos al cambiar tipo
    this.servicioPoloForm.datos.cant_puestos = null;
    this.servicioPoloForm.datos.m2 = null;
  }

  onPropietarioChange(): void {
    const tipo = this.servicioPoloForm.propietario;
    if (!this.servicioPoloForm.datos) {
      this.servicioPoloForm.datos = {};
    }

    if (tipo === 'propietario') {
      this.servicioPoloForm.datos.datos_prop = { nombre: '', contacto: '' };
      delete this.servicioPoloForm.datos.datos_inquilino;
    } else if (tipo === 'inquilino') {
      this.servicioPoloForm.datos.datos_inquilino = {
        nombre: '',
        contacto: '',
      };
      delete this.servicioPoloForm.datos.datos_prop;
    } else {
      delete this.servicioPoloForm.datos.datos_prop;
      delete this.servicioPoloForm.datos.datos_inquilino;
    }
  }

  deleteServicioPolo(id: number): void {
    if (confirm('¿Está seguro de que desea eliminar este servicio del polo?')) {
      this.adminPoloService.deleteServicioPolo(id).subscribe({
        next: () => {
          this.showMessage(
            'Servicio del polo eliminado exitosamente',
            'success'
          );
          this.serviciosPolo = this.serviciosPolo.filter(
            (s) => s.id_servicio_polo !== id
          );
        },
        error: (error) => {
          this.showMessage(
            'Error al eliminar servicio del polo: ' +
              (error.error?.detail || error.message),
            'error'
          );
        },
      });
    }
  }

  // LOTES
  selectedServicioPoloId: number | null = null;

  openLoteForm(idServicioPolo: number, nombreServicio?: string): void {
    this.selectedServicioPoloId = idServicioPolo;
    this.nombreServicioSeleccionado = nombreServicio || '';

    this.loteForm = {
      dueno: '',
      lote: 0,
      manzana: 0,
      id_servicio_polo: idServicioPolo,
    };

    this.showLoteForm = true;
  }

  onSubmitLote(): void {
    this.loading = true;

    // Por si acaso querés setear el ID explícitamente
    if (this.selectedServicioPoloId !== null) {
      this.loteForm.id_servicio_polo = this.selectedServicioPoloId;
    }

    this.adminPoloService.createLote(this.loteForm).subscribe({
      next: (lote) => {
        this.showMessage('Lote creado exitosamente', 'success');
        this.lotes.push(lote);
        this.resetForms();
        this.loading = false;
      },
      error: (error) => {
        this.showMessage(
          'Error al crear lote: ' + (error.error?.detail || error.message),
          'error'
        );
        this.loading = false;
      },
    });
  }

  deleteLote(id: number): void {
    if (confirm('¿Está seguro de que desea eliminar este lote?')) {
      this.adminPoloService.deleteLote(id).subscribe({
        next: () => {
          this.showMessage('Lote eliminado exitosamente', 'success');
          this.lotes = this.lotes.filter((l) => l.id_lotes !== id);
        },
        error: (error) => {
          this.showMessage(
            'Error al eliminar lote: ' + (error.error?.detail || error.message),
            'error'
          );
        },
      });
    }
  }

  getRoleName(id: number): string {
    const rol = this.roles.find((r) => r.id_rol === id);
    return rol ? rol.tipo_rol : 'Desconocido';
  }

  private validatePassword(password: string): string | null {
    if (!password) {
      return 'La contraseña es requerida';
    }

    if (password.length < 6) {
      return 'La contraseña debe tener al menos 6 caracteres';
    }

    if (!/[A-Z]/.test(password)) {
      return 'La contraseña debe contener al menos una mayúscula';
    }

    if (!/[a-z]/.test(password)) {
      return 'La contraseña debe contener al menos una minúscula';
    }

    if (!/[0-9]/.test(password)) {
      return 'La contraseña debe contener al menos un número';
    }

    return null;
  }

  createUsuarioForEmpresa(empresa: Empresa): void {
    console.log('🚀 createUsuarioForEmpresa ejecutado con:', empresa);
    this.selectedEmpresa = empresa;
    this.creatingForEmpresa = true;
    this.usuarioForm = {
      email: '',
      nombre: '',
      password: '',
      estado: true,
      cuil: empresa.cuil,
      id_rol: 0,
    };
    console.log('📝 Formulario configurado:', this.usuarioForm);
    console.log('🔧 Abriendo formulario...');
    this.showUsuarioForm = true;
    console.log('✅ showUsuarioForm =', this.showUsuarioForm);
  }

  createServicioPoloForEmpresa(empresa: Empresa): void {
    console.log('🚀 createServicioPoloForEmpresa ejecutado con:', empresa);
    this.selectedEmpresa = empresa;
    this.creatingForEmpresa = true;
    this.servicioPoloForm = {
      nombre: '',
      horario: '',
      datos: {},
      propietario: '',
      id_tipo_servicio_polo: 1,
      cuil: empresa.cuil,
    };
    this.showServicioPoloForm = true;
    console.log('✅ showServicioPoloForm =', this.showServicioPoloForm);
  }

  createLoteForEmpresa(empresa: Empresa): void {
    console.log('🚀 createLoteForEmpresa ejecutado con:', empresa);
    this.selectedEmpresa = empresa;
    this.creatingForEmpresa = true;
    this.loteForm = {
      dueno: '',
      lote: 0,
      manzana: 0,
      id_servicio_polo: 0,
    };
    this.showLoteForm = true;
    console.log('✅ showLoteForm =', this.showLoteForm);
  }

  openLoteFormForEmpresa(empresa: Empresa): void {
    // Aquí podrías cargar los servicios del polo de esta empresa específica
    this.loteForm = {
      dueno: '',
      lote: 0,
      manzana: 0,
      id_servicio_polo: 0, // El usuario tendrá que seleccionar de los servicios de esta empresa
    };
    this.showLoteForm = true;
  }
}
