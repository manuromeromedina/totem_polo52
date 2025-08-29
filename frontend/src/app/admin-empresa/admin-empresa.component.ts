import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgxJsonViewerModule } from 'ngx-json-viewer';

import { AuthenticationService } from '../auth/auth.service'; // Agregar esta línea

import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import {
  AdminEmpresaService,
  Vehiculo,
  VehiculoCreate,
  Servicio,
  ServicioCreate,
  ServicioUpdate,
  Contacto,
  ContactoCreate,
  EmpresaDetail,
  EmpresaSelfUpdate,
  UserUpdateCompany,
  TipoVehiculo,
  TipoServicio,
  TipoContacto,
  TipoServicioPolo,
} from './admin-empresa.service';
import { LogoutButtonComponent } from '../shared/logout-button/logout-button.component';
import {
  PasswordChangeModalComponent, // Solo importar PasswordErrors
} from '../shared/password-change-modal/password-change-modal.component';

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
  selector: 'app-empresa-me',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    LogoutButtonComponent,
    NgxJsonViewerModule,
    PasswordChangeModalComponent,
  ],
  templateUrl: './admin-empresa.component.html',
  styleUrls: ['./admin-empresa.component.css'],
})
export class EmpresaMeComponent implements OnInit {
  activeTab = 'perfil';

  // Datos de la empresa
  empresaData: EmpresaDetail | null = null;

  // Formularios
  showPasswordForm = false;
  showVehiculoForm = false;
  showServicioForm = false;
  showContactoForm = false;
  showEmpresaEditForm = false;

  // Estados de edición
  editingVehiculo: Vehiculo | null = null;
  editingServicio: Servicio | null = null;
  editingContacto: Contacto | null = null;

  // PROPIEDADES PARA CONTROL DE CAMBIOS
  private initialForms: { [key: string]: any } = {};
  private hasUnsavedChanges: { [key: string]: boolean } = {};

  // Formularios
  passwordForm = {
    password: '',
    confirmPassword: '',
  };

  vehiculoForm: VehiculoCreate = {
    id_tipo_vehiculo: 1,
    horarios: '',
    frecuencia: '',
    datos: {},
  };

  servicioForm: ServicioCreate = {
    datos: {},
    id_tipo_servicio: 1,
  };

  contactoForm: ContactoCreate = {
    id_tipo_contacto: 1,
    nombre: '',
    telefono: '',
    datos: {},
    direccion: '',
    id_servicio_polo: 1,
  };

  empresaEditForm: EmpresaSelfUpdate = {
    cant_empleados: 0,
    observaciones: '',
    horario_trabajo: '',
  };

  // Estados
  loading = false;
  loadingTipos = false;
  message = '';
  messageType: 'success' | 'error' = 'success';

  // Sistema de errores mejorado
  formErrors: { [key: string]: FormError[] } = {};
  showErrorDetails = false;

  // Tipos desde la BD
  tiposVehiculo: TipoVehiculo[] = [];
  tiposServicio: TipoServicio[] = [];
  tiposContacto: TipoContacto[] = [];
  tiposServicioPolo: TipoServicioPolo[] = [];

  // PROPIEDADES PARA BÚSQUEDA
  vehiculoSearchTerm: string = '';
  servicioSearchTerm: string = '';
  contactoSearchTerm: string = '';
  servicioPoloSearchTerm: string = '';

  // Arrays filtrados
  filteredVehiculos: Vehiculo[] = [];
  filteredServicios: Servicio[] = [];
  filteredContactos: Contacto[] = [];
  filteredServiciosPolo: any[] = [];

  // Expanded rows
  expandedRows = new Set<string>();

  constructor(
    private adminEmpresaService: AdminEmpresaService,
    private authService: AuthenticationService
  ) {}
  public isDarkMode: boolean = false;

  ngOnInit(): void {
    this.loadTipos();
    this.loadEmpresaData();

    const savedTheme = localStorage.getItem('theme');
    this.isDarkMode = savedTheme === 'dark';

    // Aplicar tema inicial
    if (this.isDarkMode) {
      document.body.style.background = '#1a1a1a';
      document.documentElement.style.background = '#1a1a1a';
    }
  }

  toggleDarkMode(): void {
    this.isDarkMode = !this.isDarkMode;
    localStorage.setItem('theme', this.isDarkMode ? 'dark' : 'light');

    // Aplicar tema al body y html
    const body = document.body;
    const html = document.documentElement;

    if (this.isDarkMode) {
      body.style.background = '#1a1a1a';
      body.style.margin = '0';
      body.style.padding = '0';
      html.style.background = '#1a1a1a';
    } else {
      body.style.background = '#f8f9fa';
      html.style.background = '#ffffff';
    }
  }

  setActiveTab(tab: string): void {
    this.activeTab = tab;
    // Cerrar formularios sin confirmación al cambiar de tab
    this.closeAllFormsWithoutConfirmation();
    // Aplicar filtros al cambiar de pestaña
    this.applyFilters();
  }

  // MÉTODO PARA CERRAR TODOS LOS FORMULARIOS SIN CONFIRMACIÓN
  private closeAllFormsWithoutConfirmation(): void {
    this.showPasswordForm = false;
    this.showVehiculoForm = false;
    this.showServicioForm = false;
    this.showContactoForm = false;
    this.showEmpresaEditForm = false;
    this.editingVehiculo = null;
    this.editingServicio = null;
    this.editingContacto = null;

    // Limpiar errores de todos los formularios
    this.formErrors = {};

    // Limpiar estados de cambios
    this.initialForms = {};
    this.hasUnsavedChanges = {};
  }

  // MÉTODOS PARA CONTROL DE CAMBIOS

  // 1. MÉTODO PARA GUARDAR ESTADO INICIAL MEJORADO
  private saveInitialFormState(formName: string, formData: any): void {
    // Crear copia profunda inmediatamente
    this.initialForms[formName] = JSON.parse(JSON.stringify(formData));
    this.hasUnsavedChanges[formName] = false;

    // 🔧 DEBUG: Verificar que se guardó correctamente
    console.log(
      `💾 Estado inicial guardado para ${formName}:`,
      this.initialForms[formName]
    );
  }

  private hasFormChanged(formName: string, currentFormData: any): boolean {
    if (!this.initialForms[formName]) return false;

    const initial = JSON.stringify(this.initialForms[formName]);
    const current = JSON.stringify(currentFormData);

    return initial !== current;
  }

  private checkUnsavedChanges(formName: string, currentFormData: any): boolean {
    return this.hasFormChanged(formName, currentFormData);
  }

  // MÉTODO PARA RESTAURAR DATOS ORIGINALES
  private restoreOriginalFormData(formName: string): void {
    console.log(`🔄 Restaurando datos para ${formName}`);

    if (!this.initialForms[formName]) {
      console.error('❌ No hay datos iniciales guardados para', formName);
      return;
    }

    // Crear copia profunda de los datos originales
    const originalData = JSON.parse(
      JSON.stringify(this.initialForms[formName])
    );
    console.log('📋 Datos originales a restaurar:', originalData);

    switch (formName) {
      case 'vehiculo':
        this.vehiculoForm = {
          id_tipo_vehiculo: originalData.id_tipo_vehiculo,
          horarios: originalData.horarios,
          frecuencia: originalData.frecuencia,
          datos: { ...originalData.datos },
        };
        console.log('✅ Vehículo restaurado:', this.vehiculoForm);
        break;

      case 'servicio':
        this.servicioForm = {
          id_tipo_servicio: originalData.id_tipo_servicio,
          datos: { ...originalData.datos },
        };
        console.log('✅ Servicio restaurado:', this.servicioForm);
        break;

      case 'contacto':
        this.contactoForm = {
          id_tipo_contacto: originalData.id_tipo_contacto,
          nombre: originalData.nombre,
          telefono: originalData.telefono,
          direccion: originalData.direccion,
          id_servicio_polo: originalData.id_servicio_polo,
          datos: { ...originalData.datos },
        };
        console.log('✅ Contacto restaurado:', this.contactoForm);
        break;

      case 'empresa':
        this.empresaEditForm = {
          cant_empleados: originalData.cant_empleados,
          observaciones: originalData.observaciones,
          horario_trabajo: originalData.horario_trabajo,
        };
        console.log('✅ Empresa restaurada:', this.empresaEditForm);
        break;

      case 'password':
        this.passwordForm = {
          password: originalData.password,
          confirmPassword: originalData.confirmPassword,
        };
        console.log('✅ Password restaurado:', this.passwordForm);
        break;
    }
  }

  // MÉTODO PARA CANCELAR FORMULARIOS CON CONFIRMACIÓN DE CAMBIOS
  cancelForm(formName: string): void {
    let currentFormData: any;

    // Obtener los datos actuales del formulario
    switch (formName) {
      case 'vehiculo':
        currentFormData = this.vehiculoForm;
        break;
      case 'servicio':
        currentFormData = this.servicioForm;
        break;
      case 'contacto':
        currentFormData = this.contactoForm;
        break;
      case 'empresa':
        currentFormData = this.empresaEditForm;
        break;
      case 'password':
        currentFormData = this.passwordForm;
        break;
      default:
        return;
    }

    // 🔧 DEBUG: Verificar estados
    console.log(`🔍 Cancelando formulario ${formName}`);
    console.log('📄 Datos actuales:', currentFormData);
    console.log('💾 Datos iniciales guardados:', this.initialForms[formName]);

    // Verificar si hay cambios sin guardar
    const hasChanges = this.checkUnsavedChanges(formName, currentFormData);
    console.log('🔄 ¿Hay cambios?', hasChanges);

    if (hasChanges) {
      const shouldDiscard = confirm(
        '¿Deseas descartar los cambios?\n\n' +
          'Se perderán todos los cambios no guardados.\n\n' +
          'Presiona "Aceptar" para descartar o "Cancelar" para continuar editando.'
      );

      console.log('👤 Usuario eligió descartar:', shouldDiscard);

      if (!shouldDiscard) {
        return; // Usuario decide continuar editando
      }

      // Restaurar datos originales ANTES de cerrar
      console.log('🔄 Restaurando datos originales...');
      this.restoreOriginalFormData(formName);
    }

    // Cerrar el formulario
    this.closeFormWithoutConfirmation(formName);
  }
  // MÉTODO PARA CERRAR FORMULARIO SIN CONFIRMACIÓN (uso interno)
  private closeFormWithoutConfirmation(formName: string): void {
    switch (formName) {
      case 'vehiculo':
        this.showVehiculoForm = false;
        this.editingVehiculo = null;
        break;
      case 'servicio':
        this.showServicioForm = false;
        this.editingServicio = null;
        break;
      case 'contacto':
        this.showContactoForm = false;
        this.editingContacto = null;
        break;
      case 'empresa':
        this.showEmpresaEditForm = false;
        break;
      case 'password':
        this.showPasswordForm = false;
        break;
    }

    // Limpiar errores específicos del formulario
    this.clearFormErrors(formName);

    // Limpiar estado de cambios para este formulario
    delete this.initialForms[formName];
    delete this.hasUnsavedChanges[formName];
  }

  closeFormDirectly(formName: string): void {
    // Este método se usa para el botón X y hace la misma validación
    this.cancelForm(formName);
  }

  // MÉTODOS DE FILTRADO
  applyFilters(): void {
    switch (this.activeTab) {
      case 'vehiculos':
        this.filterVehiculos();
        break;
      case 'servicios':
        this.filterServicios();
        break;
      case 'contactos':
        this.filterContactos();
        break;
      case 'serviciosPolo':
        this.filterServiciosPolo();
        break;
    }
  }

  filterVehiculos(): void {
    if (!this.empresaData?.vehiculos) {
      this.filteredVehiculos = [];
      return;
    }

    if (!this.vehiculoSearchTerm.trim()) {
      this.filteredVehiculos = [...this.empresaData.vehiculos];
      return;
    }

    const term = this.vehiculoSearchTerm.toLowerCase().trim();
    this.filteredVehiculos = this.empresaData.vehiculos.filter(
      (vehiculo) =>
        this.getTipoVehiculoName(vehiculo.id_tipo_vehiculo)
          .toLowerCase()
          .includes(term) ||
        vehiculo.horarios.toLowerCase().includes(term) ||
        vehiculo.frecuencia.toLowerCase().includes(term) ||
        (vehiculo.datos.patente &&
          vehiculo.datos.patente.toLowerCase().includes(term)) ||
        (vehiculo.datos.carga &&
          vehiculo.datos.carga.toLowerCase().includes(term))
    );
  }

  clearVehiculoSearch(): void {
    this.vehiculoSearchTerm = '';
    this.filteredVehiculos = this.empresaData?.vehiculos
      ? [...this.empresaData.vehiculos]
      : [];
  }

  filterServicios(): void {
    if (!this.empresaData?.servicios) {
      this.filteredServicios = [];
      return;
    }

    if (!this.servicioSearchTerm.trim()) {
      this.filteredServicios = [...this.empresaData.servicios];
      return;
    }

    const term = this.servicioSearchTerm.toLowerCase().trim();
    this.filteredServicios = this.empresaData.servicios.filter(
      (servicio) =>
        this.getTipoServicioName(servicio.id_tipo_servicio)
          .toLowerCase()
          .includes(term) ||
        JSON.stringify(servicio.datos).toLowerCase().includes(term)
    );
  }

  clearServicioSearch(): void {
    this.servicioSearchTerm = '';
    this.filteredServicios = this.empresaData?.servicios
      ? [...this.empresaData.servicios]
      : [];
  }

  filterContactos(): void {
    if (!this.empresaData?.contactos) {
      this.filteredContactos = [];
      return;
    }

    if (!this.contactoSearchTerm.trim()) {
      this.filteredContactos = [...this.empresaData.contactos];
      return;
    }

    const term = this.contactoSearchTerm.toLowerCase().trim();
    this.filteredContactos = this.empresaData.contactos.filter(
      (contacto) =>
        contacto.nombre.toLowerCase().includes(term) ||
        this.getTipoContactoName(contacto.id_tipo_contacto)
          .toLowerCase()
          .includes(term) ||
        (contacto.telefono && contacto.telefono.toLowerCase().includes(term)) ||
        (contacto.direccion &&
          contacto.direccion.toLowerCase().includes(term)) ||
        (contacto.datos?.correo &&
          contacto.datos.correo.toLowerCase().includes(term)) ||
        (contacto.datos?.pagina_web &&
          contacto.datos.pagina_web.toLowerCase().includes(term))
    );
  }

  clearContactoSearch(): void {
    this.contactoSearchTerm = '';
    this.filteredContactos = this.empresaData?.contactos
      ? [...this.empresaData.contactos]
      : [];
  }

  filterServiciosPolo(): void {
    if (!this.empresaData?.servicios_polo) {
      this.filteredServiciosPolo = [];
      return;
    }

    if (!this.servicioPoloSearchTerm.trim()) {
      this.filteredServiciosPolo = [...this.empresaData.servicios_polo];
      return;
    }

    const term = this.servicioPoloSearchTerm.toLowerCase().trim();
    this.filteredServiciosPolo = this.empresaData.servicios_polo.filter(
      (servicio) =>
        (servicio.nombre && servicio.nombre.toLowerCase().includes(term)) ||
        this.getTipoServicioPoloName(servicio.id_tipo_servicio_polo)
          .toLowerCase()
          .includes(term) ||
        (servicio.horario && servicio.horario.toLowerCase().includes(term)) ||
        (servicio.propietario &&
          servicio.propietario.toLowerCase().includes(term))
    );
  }

  clearServicioPoloSearch(): void {
    this.servicioPoloSearchTerm = '';
    this.filteredServiciosPolo = this.empresaData?.servicios_polo
      ? [...this.empresaData.servicios_polo]
      : [];
  }

  // Método para limpiar errores específicos
  clearFormErrors(formName: string): void {
    this.formErrors[formName] = [];
  }

  // Método para obtener errores de un campo específico
  getFieldErrors(formName: string, fieldName: string): FormError[] {
    const errors = this.formErrors[formName] || [];
    return errors.filter((error) => error.field === fieldName);
  }

  // Método para verificar si un campo tiene errores
  hasFieldError(formName: string, fieldName: string): boolean {
    return this.getFieldErrors(formName, fieldName).length > 0;
  }

  // Procesador de errores HTTP mejorado
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

  // Traductor de errores de campos específicos
  private translateFieldError(
    field: string,
    message: string,
    formName: string
  ): string {
    const translations: { [key: string]: { [key: string]: string } } = {
      vehiculo: {
        id_tipo_vehiculo: 'El tipo de vehículo es requerido',
        horarios: 'Los horarios son requeridos (formato: HH:MM - HH:MM)',
        frecuencia: 'La frecuencia es requerida',
        'datos.cantidad': 'La cantidad debe ser mayor a 0',
        'datos.patente':
          'La patente debe tener formato válido (ABC123 o AB123CD)',
        'datos.carga': 'Seleccione un tipo de carga válido',
        'datos.m2': 'Los metros cuadrados deben ser mayor a 0',
      },
      servicio: {
        id_tipo_servicio: 'El tipo de servicio es requerido',
        'datos.biofiltro': 'Debe especificar si tiene biofiltro',
        'datos.tratamiento_aguas_grises':
          'Debe especificar el tratamiento de aguas grises',
        'datos.abierto': 'Debe especificar si está abierto al público',
        'datos.m2': 'Los metros cuadrados son requeridos y deben ser mayor a 0',
        'datos.tipo': 'El tipo es requerido',
        'datos.proveedor': 'El proveedor es requerido',
        'datos.cantidad': 'La cantidad es requerida y debe ser mayor a 0',
      },
      contacto: {
        nombre: 'El nombre es requerido (mínimo 2 caracteres)',
        id_tipo_contacto: 'El tipo de contacto es requerido',
        telefono: 'El teléfono debe tener formato válido',
        direccion: 'La dirección es requerida para contactos comerciales',
        id_servicio_polo: 'El ID del servicio polo es requerido',
        'datos.pagina_web':
          'La página web debe tener formato válido (https://)',
        'datos.correo': 'El correo debe tener formato válido',
        'datos.redes_sociales':
          'Las redes sociales son requeridas para contactos comerciales',
      },
      empresa: {
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

  // Traductor de errores genéricos
  private translateGenericError(detail: string, formName: string): string {
    const translations: { [key: string]: string } = {
      'Ya existe un vehículo con esa patente':
        'Ya existe un vehículo registrado con esa patente',
      'Ya existe un contacto con ese nombre':
        'Ya existe un contacto registrado con ese nombre',
      'Usuario no encontrado': 'Usuario no encontrado en el sistema',
      'Email no registrado': 'El email no está registrado en el sistema',
      'Credenciales inválidas': 'Usuario o contraseña incorrectos',
      'Token inválido':
        'La sesión ha expirado, por favor inicie sesión nuevamente',
      'Servicio no encontrado': 'El servicio solicitado no existe',
      'Vehículo no encontrado': 'El vehículo solicitado no existe',
      'Contacto no encontrado': 'El contacto solicitado no existe',
      'Empresa no encontrada': 'La empresa no fue encontrada',
      'Rol inválido': 'El rol especificado no es válido',
      'Acceso denegado': 'No tiene permisos para realizar esta acción',
      'Datos inválidos': 'Los datos enviados contienen errores',
    };

    return translations[detail] || detail;
  }

  loadEmpresaData(): void {
    this.loading = true;
    this.clearFormErrors('general');

    this.adminEmpresaService.getMyCompanyDetails().subscribe({
      next: (data) => {
        this.empresaData = data;
        this.empresaEditForm = {
          cant_empleados: data.cant_empleados,
          observaciones: data.observaciones || '',
          horario_trabajo: data.horario_trabajo,
        };

        // Inicializar arrays filtrados
        this.filteredVehiculos = [...(data.vehiculos || [])];
        this.filteredServicios = [...(data.servicios || [])];
        this.filteredContactos = [...(data.contactos || [])];
        this.filteredServiciosPolo = [...(data.servicios_polo || [])];

        this.loading = false;
      },
      error: (error) => {
        this.handleError(error, 'general', 'cargar datos de la empresa');
        this.loading = false;
      },
    });
  }

  // Método resetForms sin confirmación (usado al enviar exitosamente)
  resetForms(): void {
    this.showPasswordForm = false;
    this.showVehiculoForm = false;
    this.showServicioForm = false;
    this.showContactoForm = false;
    this.showEmpresaEditForm = false;
    this.editingVehiculo = null;
    this.editingServicio = null;
    this.editingContacto = null;
    this.message = '';

    // Limpiar errores de todos los formularios
    this.formErrors = {};

    // Resetear formularios
    this.passwordForm = { password: '', confirmPassword: '' };
    this.vehiculoForm = {
      id_tipo_vehiculo: 1,
      horarios: '',
      frecuencia: '',
      datos: {},
    };
    this.servicioForm = { datos: {}, id_tipo_servicio: 1 };
    this.contactoForm = {
      id_tipo_contacto: 1,
      nombre: '',
      telefono: '',
      datos: {
        pagina_web: '',
        correo: '',
        redes_sociales: '',
      },
      direccion: '',
      id_servicio_polo: 1,
    };

    // Limpiar estados de cambios
    this.initialForms = {};
    this.hasUnsavedChanges = {};
  }

  showMessage(message: string, type: 'success' | 'error'): void {
    this.message = message;
    this.messageType = type;
    setTimeout(() => {
      this.message = '';
    }, 5000);
  }

  openPasswordForm(): void {
    console.log(
      '🔐 Abriendo modal de cambio de contraseña para usuario logueado'
    );
    this.clearFormErrors('password');
    this.showPasswordForm = true;
    // No necesitamos saveInitialFormState aquí porque el modal maneja su propio estado
  }

  // EMPRESA EDIT
  openEmpresaEditForm(): void {
    this.clearFormErrors('empresa');
    this.showEmpresaEditForm = true;

    // 🔧 IMPORTANTE: Guardar el estado inicial DESPUÉS de mostrar el formulario
    setTimeout(() => {
      this.saveInitialFormState('empresa', this.empresaEditForm);
    }, 0);
  }

  onSubmitEmpresaEdit(): void {
    this.loading = true;
    this.clearFormErrors('empresa');

    this.adminEmpresaService.updateMyCompany(this.empresaEditForm).subscribe({
      next: () => {
        this.showMessage(
          'Datos de empresa actualizados exitosamente',
          'success'
        );
        this.loadEmpresaData();
        this.resetForms();
        this.loading = false;
      },
      error: (error) => {
        this.handleError(error, 'empresa', 'actualizar datos de empresa');
        this.loading = false;
      },
    });
  }

  // VEHÍCULOS
  openVehiculoForm(vehiculo?: Vehiculo): void {
    this.clearFormErrors('vehiculo');

    if (vehiculo) {
      this.editingVehiculo = vehiculo;
      this.vehiculoForm = {
        id_tipo_vehiculo: vehiculo.id_tipo_vehiculo,
        horarios: vehiculo.horarios,
        frecuencia: vehiculo.frecuencia,
        datos: { ...vehiculo.datos }, // Copia profunda
      };
    } else {
      this.editingVehiculo = null;
      this.vehiculoForm = {
        id_tipo_vehiculo: 1,
        horarios: '',
        frecuencia: '',
        datos: {},
      };
    }

    this.showVehiculoForm = true;

    // 🔧 IMPORTANTE: Guardar estado después de configurar el formulario
    setTimeout(() => {
      this.saveInitialFormState('vehiculo', this.vehiculoForm);
    }, 0);
  }

  onSubmitVehiculo(): void {
    this.loading = true;
    this.clearFormErrors('vehiculo');

    if (this.editingVehiculo) {
      this.adminEmpresaService
        .updateVehiculo(this.editingVehiculo.id_vehiculo, this.vehiculoForm)
        .subscribe({
          next: () => {
            this.showMessage('Vehículo actualizado exitosamente', 'success');
            this.loadEmpresaData();
            this.resetForms();
            this.loading = false;
          },
          error: (error) => {
            this.handleError(error, 'vehiculo', 'actualizar vehículo');
            this.loading = false;
          },
        });
    } else {
      this.adminEmpresaService.createVehiculo(this.vehiculoForm).subscribe({
        next: () => {
          this.showMessage('Vehículo creado exitosamente', 'success');
          this.loadEmpresaData();
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          this.handleError(error, 'vehiculo', 'crear vehículo');
          this.loading = false;
        },
      });
    }
  }

  deleteVehiculo(id: number): void {
    if (confirm('¿Está seguro de que desea eliminar este vehículo?')) {
      this.adminEmpresaService.deleteVehiculo(id).subscribe({
        next: () => {
          this.showMessage('Vehículo eliminado exitosamente', 'success');
          this.loadEmpresaData();
        },
        error: (error) => {
          this.handleError(error, 'general', 'eliminar vehículo');
        },
      });
    }
  }

  // SERVICIOS
  openServicioForm(servicio?: Servicio): void {
    this.clearFormErrors('servicio');

    if (servicio) {
      this.editingServicio = servicio;
      this.servicioForm = {
        id_tipo_servicio: servicio.id_tipo_servicio,
        datos: { ...servicio.datos },
      };
    } else {
      this.editingServicio = null;
      this.servicioForm = {
        id_tipo_servicio: 1,
        datos: {},
      };
    }

    // Configurar datos según tipo
    this.onTipoServicioChange();

    // Si estamos editando, restaurar los datos específicos
    if (this.editingServicio) {
      this.servicioForm.datos = { ...servicio!.datos };
    }

    this.showServicioForm = true;

    // 🔧 IMPORTANTE: Guardar estado después de todas las configuraciones
    setTimeout(() => {
      this.saveInitialFormState('servicio', this.servicioForm);
    }, 0);
  }

  onSubmitServicio(): void {
    this.loading = true;
    this.clearFormErrors('servicio');

    if (this.editingServicio) {
      const updateData: ServicioUpdate = {
        datos: this.servicioForm.datos,
        id_tipo_servicio: this.servicioForm.id_tipo_servicio,
      };

      this.adminEmpresaService
        .updateServicio(this.editingServicio.id_servicio, updateData)
        .subscribe({
          next: () => {
            this.showMessage('Servicio actualizado exitosamente', 'success');
            this.loadEmpresaData();
            this.resetForms();
            this.loading = false;
          },
          error: (error) => {
            this.handleError(error, 'servicio', 'actualizar servicio');
            this.loading = false;
          },
        });
    } else {
      this.adminEmpresaService.createServicio(this.servicioForm).subscribe({
        next: () => {
          this.showMessage('Servicio creado exitosamente', 'success');
          this.loadEmpresaData();
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          this.handleError(error, 'servicio', 'crear servicio');
          this.loading = false;
        },
      });
    }
  }

  deleteServicio(id: number): void {
    if (confirm('¿Está seguro de que desea eliminar este servicio?')) {
      this.adminEmpresaService.deleteServicio(id).subscribe({
        next: () => {
          this.showMessage('Servicio eliminado exitosamente', 'success');
          this.loadEmpresaData();
        },
        error: (error) => {
          this.handleError(error, 'general', 'eliminar servicio');
        },
      });
    }
  }

  onTipoServicioChange(): void {
    this.servicioForm.datos = {};

    switch (this.servicioForm.id_tipo_servicio) {
      case 1:
        this.servicioForm.datos = {
          biofiltro: '',
          tratamiento_aguas_grises: '',
        };
        break;
      case 2:
        this.servicioForm.datos = {
          abierto: '',
          m2: null,
        };
        break;
      case 3:
        this.servicioForm.datos = {
          tipo: '',
          proveedor: '',
        };
        break;
      case 4:
        this.servicioForm.datos = {
          tipo: '',
          cantidad: null,
        };
        break;
      default:
        this.servicioForm.datos = {};
    }
  }

  // CONTACTOS
  openContactoForm(contacto?: Contacto): void {
    this.clearFormErrors('contacto');

    if (contacto) {
      this.editingContacto = contacto;
      this.contactoForm = {
        id_tipo_contacto: contacto.id_tipo_contacto,
        nombre: contacto.nombre,
        telefono: contacto.telefono || '',
        datos: contacto.datos
          ? { ...contacto.datos }
          : {
              pagina_web: '',
              correo: '',
              redes_sociales: '',
              direccion: '',
            },
        direccion: contacto.direccion || '',
        id_servicio_polo: contacto.id_servicio_polo,
      };
    } else {
      this.editingContacto = null;
      this.contactoForm = {
        id_tipo_contacto: 1,
        nombre: '',
        telefono: '',
        datos: {
          pagina_web: '',
          correo: '',
          redes_sociales: '',
          direccion: '',
        },
        direccion: '',
        id_servicio_polo: 1,
      };
    }

    this.showContactoForm = true;
    this.onTipoContactoChange();

    // 🔧 IMPORTANTE: Guardar estado después de todas las configuraciones
    setTimeout(() => {
      this.saveInitialFormState('contacto', this.contactoForm);
    }, 0);
  }

  onTipoContactoChange(): void {
    const tipo = Number(this.contactoForm.id_tipo_contacto);

    if (tipo === 1) {
      this.contactoForm.datos = {
        pagina_web: this.contactoForm.datos.pagina_web || '',
        correo: this.contactoForm.datos.correo || '',
        redes_sociales: this.contactoForm.datos.redes_sociales || '',
        direccion:
          this.contactoForm.direccion ||
          this.contactoForm.datos.direccion ||
          '',
      };
    } else {
      this.contactoForm.datos = {};
    }
  }

  onSubmitContacto(): void {
    this.loading = true;
    this.clearFormErrors('contacto');

    // Validación adicional antes de enviar
    if (this.esTipoComercial()) {
      if (this.contactoForm.direccion) {
        this.contactoForm.datos.direccion = this.contactoForm.direccion;
      } else if (this.contactoForm.datos.direccion) {
        this.contactoForm.direccion = this.contactoForm.datos.direccion;
      }

      if (
        !this.contactoForm.datos.direccion ||
        this.contactoForm.datos.direccion.trim() === ''
      ) {
        this.formErrors['contacto'] = [
          {
            field: 'direccion',
            message: 'La dirección es requerida para contactos comerciales',
            type: 'required',
          },
        ];
        this.showMessage(
          'La dirección es requerida para contactos comerciales',
          'error'
        );
        this.loading = false;
        return;
      }
    }

    if (this.editingContacto) {
      this.adminEmpresaService
        .updateContacto(this.editingContacto.id_contacto, this.contactoForm)
        .subscribe({
          next: () => {
            this.showMessage('Contacto actualizado exitosamente', 'success');
            this.loadEmpresaData();
            this.resetForms();
            this.loading = false;
          },
          error: (error) => {
            this.handleError(error, 'contacto', 'actualizar contacto');
            this.loading = false;
          },
        });
    } else {
      this.adminEmpresaService.createContacto(this.contactoForm).subscribe({
        next: () => {
          this.showMessage('Contacto creado exitosamente', 'success');
          this.loadEmpresaData();
          this.resetForms();
          this.loading = false;
        },
        error: (error) => {
          this.handleError(error, 'contacto', 'crear contacto');
          this.loading = false;
        },
      });
    }
  }

  onDireccionChange(): void {
    if (this.esTipoComercial()) {
      this.contactoForm.datos.direccion = this.contactoForm.direccion;
    }
  }

  deleteContacto(id: number): void {
    if (confirm('¿Está seguro de que desea eliminar este contacto?')) {
      this.adminEmpresaService.deleteContacto(id).subscribe({
        next: () => {
          this.showMessage('Contacto eliminado exitosamente', 'success');
          this.loadEmpresaData();
        },
        error: (error) => {
          this.handleError(error, 'general', 'eliminar contacto');
        },
      });
    }
  }

  esTipoComercial(): boolean {
    return this.contactoForm.id_tipo_contacto === 1;
  }

  // Métodos helper
  getTipoServicioPoloName(id: number): string {
    const tipo = this.tiposServicioPolo.find(
      (t) => t.id_tipo_servicio_polo === id
    );
    return tipo ? tipo.tipo : 'Sin tipo definido';
  }

  get tieneServiciosPolo(): boolean {
    return (
      Array.isArray(this.empresaData?.servicios_polo) &&
      this.empresaData.servicios_polo.length > 0
    );
  }

  getStatusClass(activo: boolean): string {
    return activo ? 'status-active' : 'status-inactive';
  }

  formatDate(dateString: string): string {
    if (!dateString) return 'Sin fecha';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      });
    } catch (error) {
      return 'Fecha inválida';
    }
  }

  formatDatos(datos: any, isExpanded: boolean = false): string {
    if (!datos || Object.keys(datos).length === 0) {
      return 'Sin datos adicionales';
    }

    try {
      const dataString = JSON.stringify(datos, null, 2);

      if (isExpanded) {
        return dataString;
      }

      return dataString.length > 50
        ? dataString.substring(0, 50) + '...'
        : dataString;
    } catch (error) {
      return 'Error al procesar datos';
    }
  }

  getTotalLotes(): number {
    if (!this.empresaData?.servicios_polo) return 0;

    return this.empresaData.servicios_polo.reduce((total, servicio) => {
      return total + (servicio.lotes ? servicio.lotes.length : 0);
    }, 0);
  }

  getTipoVehiculoName(id: number): string {
    const tipo = this.tiposVehiculo.find((t) => t.id_tipo_vehiculo === id);
    return tipo ? tipo.tipo : 'Desconocido';
  }

  getTipoServicioName(id: number): string {
    const tipo = this.tiposServicio.find((t) => t.id_tipo_servicio === id);
    return tipo ? tipo.tipo : 'Desconocido';
  }

  getTipoContactoName(id: number): string {
    const tipo = this.tiposContacto.find((t) => t.id_tipo_contacto === id);
    return tipo ? tipo.tipo : 'Desconocido';
  }

  loadTipos(): void {
    this.loadingTipos = true;

    this.adminEmpresaService.getTiposServicioPolo().subscribe({
      next: (tipos) => {
        this.tiposServicioPolo = tipos;
      },
      error: (error) => {
        this.handleError(error, 'general', 'cargar tipos de servicio polo');
      },
    });

    this.adminEmpresaService.getTiposVehiculo().subscribe({
      next: (tipos) => {
        this.tiposVehiculo = tipos;
      },
      error: (error) => {
        this.handleError(error, 'general', 'cargar tipos de vehículo');
      },
    });

    this.adminEmpresaService.getTiposServicio().subscribe({
      next: (tipos) => {
        this.tiposServicio = tipos;
      },
      error: (error) => {
        this.handleError(error, 'general', 'cargar tipos de servicio');
      },
    });

    this.adminEmpresaService.getTiposContacto().subscribe({
      next: (tipos) => {
        this.tiposContacto = tipos;
        this.loadingTipos = false;
      },
      error: (error) => {
        this.handleError(error, 'general', 'cargar tipos de contacto');
        this.loadingTipos = false;
      },
    });
  }

  toggleExpandRow(key: string): void {
    if (this.expandedRows.has(key)) {
      this.expandedRows.delete(key);
    } else {
      this.expandedRows.add(key);
    }
  }

  hasKeys(obj: any): boolean {
    return obj && Object.keys(obj).length > 0;
  }

  // Toggle para mostrar/ocultar detalles de errores
  toggleErrorDetails(): void {
    this.showErrorDetails = !this.showErrorDetails;
  }

  // Obtener el número total de errores
  getTotalErrors(): number {
    return Object.values(this.formErrors).reduce(
      (total, errors) => total + errors.length,
      0
    );
  }

  // Obtener errores por tipo
  getErrorsByType(type: FormError['type']): FormError[] {
    const allErrors: FormError[] = [];
    Object.values(this.formErrors).forEach((errors) => {
      allErrors.push(...errors.filter((error) => error.type === type));
    });
    return allErrors;
  }

  private handlePasswordError(errorResponse: any): void {
    this.clearFormErrors('password');
    let passwordErrors: FormError[] = []; // Usar la interfaz FormError que ya tienes definida localmente

    // Error de contraseña actual incorrecta
    if (
      errorResponse.wrong_current ||
      errorResponse.error?.includes('contraseña actual') ||
      errorResponse.detail?.includes('incorrecta')
    ) {
      passwordErrors.push({
        field: 'currentPassword',
        message: 'La contraseña actual es incorrecta',
        type: 'validation',
      });
      this.showMessage('La contraseña actual es incorrecta', 'error');
    }
    // Error de contraseña reutilizada
    else if (
      errorResponse.password_reused ||
      errorResponse.error?.includes('utilizado anteriormente')
    ) {
      passwordErrors.push({
        field: 'newPassword',
        message:
          'No puedes usar una contraseña que ya hayas utilizado anteriormente',
        type: 'validation',
      });
      this.showMessage(
        'No puedes usar una contraseña que ya hayas utilizado anteriormente',
        'error'
      );
    }
    // Error de contraseñas que no coinciden
    else if (
      errorResponse.passwords_mismatch ||
      errorResponse.error?.includes('no coinciden')
    ) {
      passwordErrors.push({
        field: 'confirmPassword',
        message: 'Las contraseñas no coinciden',
        type: 'validation',
      });
      this.showMessage('Las contraseñas no coinciden', 'error');
    }
    // Errores generales
    else if (errorResponse.detail) {
      passwordErrors.push({
        field: 'general',
        message: errorResponse.detail,
        type: 'server',
      });
      this.showMessage(errorResponse.detail, 'error');
    } else if (errorResponse.error) {
      passwordErrors.push({
        field: 'general',
        message: errorResponse.error,
        type: 'server',
      });
      this.showMessage(errorResponse.error, 'error');
    } else {
      passwordErrors.push({
        field: 'general',
        message: 'Error al cambiar la contraseña. Inténtalo nuevamente.',
        type: 'server',
      });
      this.showMessage('Error al cambiar la contraseña', 'error');
    }

    // Asignar errores específicos para el modal de contraseña
    this.formErrors['password'] = passwordErrors;
  }
  showPasswordModal = false;

  openPasswordModal() {
    this.showPasswordModal = true;
    // O también puedes usar: this.passwordModal.open();
  }

  onPasswordModalClosed() {
    this.showPasswordModal = false;
    console.log('Modal de cambio de contraseña cerrado');
  }

  onPasswordChanged(success: boolean) {
    if (success) {
      console.log('✅ Contraseña cambiada exitosamente');
      // Aquí puedes mostrar una notificación de éxito
      // o actualizar algún estado en tu aplicación
    }
  }
}
