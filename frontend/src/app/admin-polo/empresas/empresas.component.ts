import { Component, OnInit } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LogoutButtonComponent } from '../../shared/logout-button/logout-button.component';

interface Empresa {
  cuil: number;
  nombre: string;
  rubro: string;
  cant_empleados: number;
  observaciones?: string;
  fecha_ingreso: string;
  horario_trabajo: string;
}

interface FiltrosEmpresa {
  busqueda: string;
  rubro: string;
  empleadosMin: number | null;
  empleadosMax: number | null;
  ordenarPor: 'nombre' | 'fecha_ingreso' | 'cant_empleados' | 'rubro';
  ordenDireccion: 'asc' | 'desc';
}

@Component({
  selector: 'app-empresas',
  standalone: true,
  imports: [CommonModule, FormsModule, LogoutButtonComponent],
  templateUrl: './empresas.component.html',
  styleUrls: ['./empresas.component.css']
})
export class EmpresasComponent implements OnInit {
  empresas: Empresa[] = [];
  empresasFiltradas: Empresa[] = [];
  loading = false;
  errorMessage = '';
  
  // Exponer Math para el template
  Math = Math;
  
  // Filtros y búsqueda
  filtros: FiltrosEmpresa = {
    busqueda: '',
    rubro: '',
    empleadosMin: null,
    empleadosMax: null,
    ordenarPor: 'nombre',
    ordenDireccion: 'asc'
  };

  // Listas para filtros
  rubrosUnicos: string[] = [];
  
  // Vista
  vistaActual: 'tabla' | 'tarjetas' = 'tabla';
  empresasPorPagina = 10;
  paginaActual = 1;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.cargarEmpresas();
  }

  cargarEmpresas(): void {
    this.loading = true;
    this.errorMessage = '';

    this.http.get<Empresa[]>('http://localhost:8000/empresas').subscribe({
      next: (data) => {
        this.empresas = data;
        this.empresasFiltradas = [...data];
        this.extraerRubrosUnicos();
        this.aplicarFiltros();
        this.loading = false;
        console.log(`Cargadas ${data.length} empresas`);
      },
      error: (err: HttpErrorResponse) => {
        this.loading = false;
        console.error('Error al cargar empresas:', err);
        
        if (err.status === 401) {
          this.errorMessage = 'Sesión expirada. Por favor, inicie sesión nuevamente.';
        } else if (err.status === 403) {
          this.errorMessage = 'No tiene permisos para ver esta información.';
        } else if (err.status === 0) {
          this.errorMessage = 'Error de conexión. Verifique su conexión a internet.';
        } else {
          this.errorMessage = 'Error al cargar las empresas. Intente nuevamente.';
        }
      }
    });
  }

  extraerRubrosUnicos(): void {
    const rubrosSet = new Set(this.empresas.map(emp => emp.rubro));
    this.rubrosUnicos = Array.from(rubrosSet).sort();
  }

  aplicarFiltros(): void {
    let resultado = [...this.empresas];

    // Filtro por búsqueda (nombre o CUIL)
    if (this.filtros.busqueda.trim()) {
      const busqueda = this.filtros.busqueda.toLowerCase().trim();
      resultado = resultado.filter(emp => 
        emp.nombre.toLowerCase().includes(busqueda) ||
        emp.cuil.toString().includes(busqueda)
      );
    }

    // Filtro por rubro
    if (this.filtros.rubro) {
      resultado = resultado.filter(emp => emp.rubro === this.filtros.rubro);
    }

    // Filtro por cantidad de empleados
    if (this.filtros.empleadosMin !== null) {
      resultado = resultado.filter(emp => emp.cant_empleados >= this.filtros.empleadosMin!);
    }
    
    if (this.filtros.empleadosMax !== null) {
      resultado = resultado.filter(emp => emp.cant_empleados <= this.filtros.empleadosMax!);
    }

    // Ordenamiento
    resultado.sort((a, b) => {
      let valorA, valorB;
      
      switch (this.filtros.ordenarPor) {
        case 'nombre':
          valorA = a.nombre.toLowerCase();
          valorB = b.nombre.toLowerCase();
          break;
        case 'fecha_ingreso':
          valorA = new Date(a.fecha_ingreso).getTime();
          valorB = new Date(b.fecha_ingreso).getTime();
          break;
        case 'cant_empleados':
          valorA = a.cant_empleados;
          valorB = b.cant_empleados;
          break;
        case 'rubro':
          valorA = a.rubro.toLowerCase();
          valorB = b.rubro.toLowerCase();
          break;
        default:
          return 0;
      }

      if (valorA < valorB) {
        return this.filtros.ordenDireccion === 'asc' ? -1 : 1;
      }
      if (valorA > valorB) {
        return this.filtros.ordenDireccion === 'asc' ? 1 : -1;
      }
      return 0;
    });

    this.empresasFiltradas = resultado;
    this.paginaActual = 1; // Resetear paginación
  }

  onBusquedaChange(): void {
    this.aplicarFiltros();
  }

  onFiltroChange(): void {
    this.aplicarFiltros();
  }

  limpiarFiltros(): void {
    this.filtros = {
      busqueda: '',
      rubro: '',
      empleadosMin: null,
      empleadosMax: null,
      ordenarPor: 'nombre',
      ordenDireccion: 'asc'
    };
    this.aplicarFiltros();
  }

  cambiarOrden(campo: 'nombre' | 'fecha_ingreso' | 'cant_empleados' | 'rubro'): void {
    if (this.filtros.ordenarPor === campo) {
      this.filtros.ordenDireccion = this.filtros.ordenDireccion === 'asc' ? 'desc' : 'asc';
    } else {
      this.filtros.ordenarPor = campo;
      this.filtros.ordenDireccion = 'asc';
    }
    this.aplicarFiltros();
  }

  cambiarVista(vista: 'tabla' | 'tarjetas'): void {
    this.vistaActual = vista;
  }

  // Paginación
  get empresasPaginadas(): Empresa[] {
    const inicio = (this.paginaActual - 1) * this.empresasPorPagina;
    const fin = inicio + this.empresasPorPagina;
    return this.empresasFiltradas.slice(inicio, fin);
  }

  get totalPaginas(): number {
    return Math.ceil(this.empresasFiltradas.length / this.empresasPorPagina);
  }

  cambiarPagina(pagina: number): void {
    if (pagina >= 1 && pagina <= this.totalPaginas) {
      this.paginaActual = pagina;
    }
  }

  get paginasArray(): number[] {
    const total = this.totalPaginas;
    const actual = this.paginaActual;
    const rango = 2;
    
    let inicio = Math.max(1, actual - rango);
    let fin = Math.min(total, actual + rango);
    
    const paginas = [];
    for (let i = inicio; i <= fin; i++) {
      paginas.push(i);
    }
    
    return paginas;
  }

  // Utilidades
  formatearFecha(fecha: string): string {
    try {
      return new Date(fecha).toLocaleDateString('es-AR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch (error) {
      return fecha;
    }
  }

  formatearCUIL(cuil: number): string {
    const cuilStr = cuil.toString();
    if (cuilStr.length === 11) {
      return `${cuilStr.substring(0, 2)}-${cuilStr.substring(2, 10)}-${cuilStr.substring(10)}`;
    }
    return cuilStr;
  }

  truncarTexto(texto: string, limite: number = 50): string {
    if (!texto) return '';
    return texto.length > limite ? texto.substring(0, limite) + '...' : texto;
  }

  obtenerIconoRubro(rubro: string): string {
    const iconos: { [key: string]: string } = {
      'Tecnología': '💻',
      'Servicios': '🔧',
      'Comercio': '🛒',
      'Industria': '🏭',
      'Educación': '📚',
      'Salud': '🏥',
      'Construcción': '🏗️',
      'Alimentación': '🍽️',
      'Transporte': '🚛',
      'Finanzas': '💰'
    };
    return iconos[rubro] || '🏢';
  }

  // Estadísticas rápidas
  get estadisticas() {
    const total = this.empresasFiltradas.length;
    const totalEmpleados = this.empresasFiltradas.reduce((sum, emp) => sum + emp.cant_empleados, 0);
    const promedioEmpleados = total > 0 ? Math.round(totalEmpleados / total) : 0;
    
    return {
      totalEmpresas: total,
      totalEmpleados,
      promedioEmpleados,
      rubrosActivos: new Set(this.empresasFiltradas.map(emp => emp.rubro)).size
    };
  }

  recargar(): void {
    this.cargarEmpresas();
  }

  exportarCSV(): void {
    const headers = ['CUIL', 'Nombre', 'Rubro', 'Empleados', 'Horario', 'Fecha Ingreso', 'Observaciones'];
    const rows = this.empresasFiltradas.map(emp => [
      this.formatearCUIL(emp.cuil),
      emp.nombre,
      emp.rubro,
      emp.cant_empleados.toString(),
      emp.horario_trabajo,
      this.formatearFecha(emp.fecha_ingreso),
      emp.observaciones || ''
    ]);

    const csvContent = [headers, ...rows]
      .map(row => row.map(cell => `"${cell}"`).join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `empresas_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // Función trackBy para optimizar el renderizado
  trackByEmpresa(index: number, empresa: Empresa): number {
    return empresa.cuil;
  }

  // Métodos auxiliares para paginación
  getPaginaInicio(): number {
    return (this.paginaActual - 1) * this.empresasPorPagina + 1;
  }

  getPaginaFin(): number {
    return Math.min(this.paginaActual * this.empresasPorPagina, this.empresasFiltradas.length);
  }
}