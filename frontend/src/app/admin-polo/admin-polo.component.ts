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
  PoloDetail,
  PoloSelfUpdate,
} from './admin-polo.service';
import { LogoutButtonComponent } from '../shared/logout-button/logout-button.component';

// Interfaces para manejo de errores
interface FormError {
  field: string;
  message: string;
  type: 'required' | 'invalid' | 'duplicate' | 'server' | 'validation';
}

interface ErrorResponse {
  detail?: string;
  message?: string;
  errors?: { [key: string]: string[] };
  status?: number;
}

@Component({
  selector: 'app-empresas',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, LogoutButtonComponent],
  templateUrl: './admin-polo.component.html',
  styleUrls: ['./admin-polo.component.css'],
})
export class AdminPoloComponent implements OnInit {
  activeTab = 'perfil'; // Cambiar tab por defecto a perfil

  // NUEVAS PROPIEDADES PARA EL POLO
  poloData: PoloDetail | null = null;
  showPasswordForm = false;
  showPoloEditForm = false;

  passwordForm = {
    password: '',
    confirmPassword: '',
  };

  poloEditForm: PoloSelfUpdate = {
    cant_empleados: 0,
    observaciones: '',
    horario_trabajo: '',
  };

  // 🔥 Sistema de errores mejorado
  formErrors: { [key: string]: FormError[] } = {};

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
    cuil: null as any,
    id_rol: null as any,
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

  // NUEVAS PROPIEDADES PARA BÚSQUEDA
  empresaSearchTerm: string = '';
  usuarioSearchTerm: string = '';
  servicioSearchTerm: string = '';
  loteSearchTerm: string = '';

  // Arrays filtrados
  filteredEmpresas: Empresa[] = [];
  filteredUsuarios: Usuario[] = [];
  filteredServicios: ServicioPolo[] = [];
  filteredLotes: Lote[] = [];

  constructor(private adminPoloService: AdminPoloService) {}

  public isDarkMode: boolean = false;

  ngOnInit(): void {
    this.loadRoles();
    // Cargar datos del polo primero
    this.loadPoloData();
    // Cargar datos de la pestaña activa por defecto
    this.loadData();
    const savedTheme = localStorage.getItem('theme');
    this.isDarkMode = savedTheme === 'dark';
  }

  toggleDarkMode(): void {
    this.isDarkMode = !this.isDarkMode;
    localStorage.setItem('theme', this.isDarkMode ? 'dark' : 'light');
  }

  setActiveTab(tab: string): void {
    this.activeTab = tab;
    this.resetForms();
    this.loadData();
  }

  // 🔥 NUEVOS MÉTODOS PARA EL POLO
  loadPoloData(): void {
    this.loading = true;
    this.clearFormErrors('general');

    this.adminPoloService.getPoloDetails().subscribe({
      next: (data) => {
        this.poloData = data;
        this.poloEditForm = {
          cant_empleados: data.cant_empleados,
          observaciones: data.observaciones || '',
          horario_trabajo: data.horario_trabajo,
        };
        this.loading = false;
      },
      error: (error) => {
        this.handleError(error, 'general', 'cargar datos del polo');
        this.loading = false;
      },
    });
  }

  // PASSWORD PARA POLO
  openPasswordForm(): void {
    this.clearFormErrors('password');
    this.showPasswordForm = true;
  }

  onSubmitPassword(): void {
    this.loading = true;
    this.clearFormErrors('password');

    this.adminPoloService.changePasswordRequest().subscribe({
      next: () => {
        this.showMessage(
          'Se ha enviado un enlace de cambio de contraseña a tu email',
          'success'
        );
        this.resetForms();
        this.loading = false;
      },
      error: (error) => {
        this.handleError(error, 'password', 'solicitar cambio de contraseña');
        this.loading = false;
      },
    });
  }

  // POLO EDIT
  openPoloEditForm(): void {
    this.clearFormErrors('polo');
    this.showPoloEditForm = true;
  }

  onSubmitPoloEdit(): void {
    this.loading = true;
    this.clearFormErrors('polo');

    this.adminPoloService.updatePolo(this.poloEditForm).subscribe({
      next: () => {
        this.showMessage('Datos del polo actualizados exitosamente', 'success');
        this.loadPoloData();
        this.resetForms();
        this.loading = false;
      },
      error: (error) => {
        this.handleError(error, 'polo', 'actualizar datos del polo');
        this.loading = false;
      },
    });
  }

  // 🔥 Método para limpiar errores específicos
  clearFormErrors(formName: string): void {
    this.formErrors[formName] = [];
  }

  // 🔥 Método para obtener errores de un campo específico
  getFieldErrors(formName: string, fieldName: string): FormError[] {
    const errors = this.formErrors[formName] || [];
    return errors.filter((error) => error.field === fieldName);
  }

  // 🔥 Método para verificar si un campo tiene errores
  hasFieldError(formName: string, fieldName: string): boolean {
    return this.getFieldErrors(formName, fieldName).length > 0;
  }

  // 🔥 Procesador de errores HTTP mejorado
  private handleError(error: any, formName: string, operation: string): void {
    console.error(`Error en ${operation}:`, error);

    this.clearFormErrors(formName);
    let errorMessages: FormError[] = [];

    if (error.status === 0) {
      errorMessages.push({
        field: 'general',
        message: 'Error de conexión. Verifique su conexión a internet.',
        type: 'server',
      });
    } else if (error.status === 401) {
      errorMessages.push({
        field: 'general',
        message: 'Sesión expirada. Por favor, inicie sesión nuevamente.',
        type: 'server',
      });
    } else if (error.status === 403) {
      errorMessages.push({
        field: 'general',
        message: 'No tiene permisos para realizar esta acción.',
        type: 'server',
      });
    } else if (error.status === 404) {
      errorMessages.push({
        field: 'general',
        message: 'El recurso solicitado no fue encontrado.',
        type: 'server',
      });
    } else if (error.status === 422) {
      // Errores de validación específicos del backend
      const errorResponse: ErrorResponse = error.error;

      if (errorResponse.errors) {
        Object.keys(errorResponse.errors).forEach((field) => {
          const fieldErrors = errorResponse.errors![field];
          fieldErrors.forEach((message) => {
            errorMessages.push({
              field: field,
              message: this.translateFieldError(field, message, formName),
              type: 'validation',
            });
          });
        });
      } else if (errorResponse.detail) {
        errorMessages.push({
          field: 'general',
          message: this.translateGenericError(errorResponse.detail, formName),
          type: 'validation',
        });
      }
    } else if (error.status === 400) {
      const errorDetail = error.error?.detail || 'Datos inválidos';
      errorMessages.push({
        field: 'general',
        message: this.translateGenericError(errorDetail, formName),
        type: 'validation',
      });
    } else if (error.status === 500) {
      errorMessages.push({
        field: 'general',
        message: 'Error interno del servidor. Intente más tarde.',
        type: 'server',
      });
    } else {
      const detail =
        error.error?.detail || error.message || 'Error desconocido';
      errorMessages.push({
        field: 'general',
        message: this.translateGenericError(detail, formName),
        type: 'server',
      });
    }

    this.formErrors[formName] = errorMessages;

    // Mostrar mensaje general
    const generalError = errorMessages.find((e) => e.field === 'general');
    if (generalError) {
      this.showMessage(generalError.message, 'error');
    } else {
      this.showMessage(
        `Error en ${operation}. Revise los campos marcados.`,
        'error'
      );
    }
  }

  // 🔥 Traductor de errores de campos específicos
  private translateFieldError(
    field: string,
    message: string,
    formName: string
  ): string {
    const translations: { [key: string]: { [key: string]: string } } = {
      polo: {
        cant_empleados: 'La cantidad de empleados debe ser mayor a 0',
        horario_trabajo: 'El horario de trabajo es requerido',
        observaciones: 'Las observaciones no pueden exceder 500 caracteres',
      },
      password: {
        password: 'La contraseña debe tener al menos 6 caracteres',
        email: 'El email no fue encontrado en el sistema',
      },
    };

    const formTranslations = translations[formName];
    if (formTranslations && formTranslations[field]) {
      return formTranslations[field];
    }

    const genericTranslations: { [key: string]: string } = {
      required: 'Este campo es requerido',
      invalid: 'El formato de este campo es inválido',
      min_length: 'Este campo es muy corto',
      max_length: 'Este campo es muy largo',
      email: 'El formato del email es inválido',
      url: 'El formato de la URL es inválido',
      number: 'Debe ser un número válido',
    };

    return genericTranslations[message] || message;
  }

  // 🔥 Traductor de errores genéricos
  private translateGenericError(detail: string, formName: string): string {
    const translations: { [key: string]: string } = {
      'Usuario no encontrado': 'Usuario no encontrado en el sistema',
      'Email no registrado': 'El email no está registrado en el sistema',
      'Credenciales inválidas': 'Usuario o contraseña incorrectos',
      'Token inválido':
        'La sesión ha expirado, por favor inicie sesión nuevamente',
      'Polo no encontrado': 'El polo no fue encontrado',
      'Acceso denegado': 'No tiene permisos para realizar esta acción',
      'Datos inválidos': 'Los datos enviados contienen errores',
    };

    return translations[detail] || detail;
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
      case 'perfil':
        // Ya se carga en ngOnInit
        this.loading = false;
        break;
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
        this.filteredEmpresas = [...empresas]; // Inicializar array filtrado
        this.filterEmpresas(); // Aplicar filtro actual si existe
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
        this.filteredUsuarios = [...usuarios]; // Inicializar array filtrado
        this.filterUsuarios(); // Aplicar filtro actual si existe
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
        this.filteredServicios = [...servicios]; // Inicializar array filtrado
        this.filterServicios(); // Aplicar filtro actual si existe
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
        this.filteredLotes = [...lotes]; // Inicializar array filtrado
        this.filterLotes(); // Aplicar filtro actual si existe
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

  // NUEVOS MÉTODOS DE FILTRADO
  filterEmpresas(): void {
    if (!this.empresaSearchTerm.trim()) {
      this.filteredEmpresas = [...this.empresas];
      return;
    }

    const term = this.empresaSearchTerm.toLowerCase().trim();
    this.filteredEmpresas = this.empresas.filter(
      (empresa) =>
        empresa.nombre.toLowerCase().includes(term) ||
        empresa.cuil.toString().includes(term) ||
        empresa.rubro.toLowerCase().includes(term)
    );
  }

  clearEmpresaSearch(): void {
    this.empresaSearchTerm = '';
    this.filteredEmpresas = [...this.empresas];
  }

  filterUsuarios(): void {
    if (!this.usuarioSearchTerm.trim()) {
      this.filteredUsuarios = [...this.usuarios];
      return;
    }

    const term = this.usuarioSearchTerm.toLowerCase().trim();
    this.filteredUsuarios = this.usuarios.filter(
      (usuario) =>
        usuario.nombre.toLowerCase().includes(term) ||
        usuario.email.toLowerCase().includes(term) ||
        usuario.cuil.toString().includes(term)
    );
  }

  clearUsuarioSearch(): void {
    this.usuarioSearchTerm = '';
    this.filteredUsuarios = [...this.usuarios];
  }

  filterServicios(): void {
    if (!this.servicioSearchTerm.trim()) {
      this.filteredServicios = [...this.serviciosPolo];
      return;
    }

    const term = this.servicioSearchTerm.toLowerCase().trim();
    this.filteredServicios = this.serviciosPolo.filter(
      (servicio) =>
        servicio.nombre.toLowerCase().includes(term) ||
        servicio.cuil.toString().includes(term) ||
        (servicio.propietario &&
          servicio.propietario.toLowerCase().includes(term))
    );
  }

  clearServicioSearch(): void {
    this.servicioSearchTerm = '';
    this.filteredServicios = [...this.serviciosPolo];
  }

  filterLotes(): void {
    if (!this.loteSearchTerm.trim()) {
      this.filteredLotes = [...this.lotes];
      return;
    }

    const term = this.loteSearchTerm.toLowerCase().trim();
    this.filteredLotes = this.lotes.filter(
      (lote) =>
        lote.dueno.toLowerCase().includes(term) ||
        lote.lote.toString().includes(term) ||
        lote.manzana.toString().includes(term)
    );
  }

  clearLoteSearch(): void {
    this.loteSearchTerm = '';
    this.filteredLotes = [...this.lotes];
  }

  resetForms(): void {
    this.showEmpresaForm = false;
    this.showUsuarioForm = false;
    this.showServicioPoloForm = false;
    this.showLoteForm = false;
    this.showPasswordForm = false;
    this.showPoloEditForm = false;
    this.editingEmpresa = null;
    this.editingUsuario = null;
    this.selectedEmpresa = null;
    this.creatingForEmpresa = false;
    this.message = '';

    // Limpiar errores de todos los formularios
    this.formErrors = {};

    this.passwordForm = { password: '', confirmPassword: '' };

    this.empresaForm = {
      cuil: 0,
      nombre: '',
      rubro: '',
      cant_empleados: 0,
      observaciones: '',
      horario_trabajo: '',
    };

    // Limpiar formulario de usuario sin contraseña para nuevos usuarios
    this.usuarioForm = {
      email: '',
      nombre: '',
      password: '', // Se mantiene para edición, pero no se usa en creación
      estado: true,
      cuil: null as any,
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
            this.loadEmpresas(); // Esto ahora actualiza los filtros también
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
          this.filteredEmpresas = [...this.empresas]; // Actualizar filtros
          this.filterEmpresas(); // Aplicar filtro actual
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
          this.loadEmpresas(); // Esto actualizará tanto el array principal como el filtrado
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
        password: '',
        estado: usuario.estado,
        cuil: usuario.cuil,
        id_rol: 0,
      };
    } else {
      this.editingUsuario = null;
      this.usuarioForm = {
        email: '',
        nombre: '',
        password: '',
        estado: true,
        cuil: null as any,
        id_rol: null as any,
      };
    }
    this.showUsuarioForm = true;
  }

  onSubmitUsuario(): void {
    this.loading = true;

    if (this.editingUsuario) {
      // Actualizar usuario existente
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
      // Crear nuevo usuario - SIN validación de contraseña

      // Validaciones básicas
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

      // Validar formato de email
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(this.usuarioForm.email)) {
        this.showMessage('El formato del email es inválido', 'error');
        this.loading = false;
        return;
      }

      // Crear el usuario sin contraseña (se genera automáticamente en el backend)
      const userCreateData = {
        email: this.usuarioForm.email,
        nombre: this.usuarioForm.nombre,
        // NO enviamos password - se genera automáticamente
        estado: this.usuarioForm.estado,
        cuil: this.usuarioForm.cuil,
        id_rol: this.usuarioForm.id_rol,
      };

      this.adminPoloService.createUser(userCreateData).subscribe({
        next: (usuario) => {
          this.showMessage(
            'Usuario creado exitosamente. Se han enviado las credenciales por email.',
            'success'
          );
          this.usuarios.push(usuario);
          this.filteredUsuarios = [...this.usuarios];
          this.filterUsuarios();
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          console.log('Error completo:', error);
          console.log('Error detail:', error.error?.detail);

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

            // Actualizar también en la lista filtrada
            const filteredIndex = this.filteredUsuarios.findIndex(
              (u) => u.id_usuario === usuario.id_usuario
            );
            if (filteredIndex !== -1) {
              this.filteredUsuarios[filteredIndex] = usuarioActualizado;
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
        this.filteredServicios = [...this.serviciosPolo]; // Actualizar filtros
        this.filterServicios(); // Aplicar filtro actual
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

    if (!this.servicioPoloForm.datos) {
      this.servicioPoloForm.datos = {};
    }

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
          this.filteredServicios = this.filteredServicios.filter(
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
    this.nombreServicioSeleccionado =
      nombreServicio || `Servicio ID: ${idServicioPolo}`;

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

    if (this.selectedServicioPoloId !== null) {
      this.loteForm.id_servicio_polo = this.selectedServicioPoloId;
    }

    this.adminPoloService.createLote(this.loteForm).subscribe({
      next: (lote) => {
        this.showMessage('Lote creado exitosamente', 'success');
        this.lotes.push(lote);
        this.filteredLotes = [...this.lotes]; // Actualizar filtros
        this.filterLotes(); // Aplicar filtro actual
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
          this.filteredLotes = this.filteredLotes.filter(
            (l) => l.id_lotes !== id
          );
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
    this.loteForm = {
      dueno: '',
      lote: 0,
      manzana: 0,
      id_servicio_polo: 0,
    };
    this.showLoteForm = true;
  }
}

// Exportar como default también si es necesario
export default AdminPoloComponent;
