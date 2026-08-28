# Sistema Inteligente de Calificación de Tareas (IA)

Un sistema web automatizado diseñado para ayudar a los docentes a optimizar el proceso de evaluación utilizando la API de Google Gemini. El sistema permite procesar entregas masivas, aplicar rúbricas personalizadas y generar retroalimentaciones detalladas de forma automática.

## Características Principales

### Módulo de Administrador
* **Gestión de Usuarios:** Creación, edición y control de cuentas para profesores.
* **Control de Cursos:** Asignación de materias y asignaturas específicas a cada docente.

### Módulo de Profesor
* **Carga Masiva de Tareas:** Soporte para subir archivos comprimidos en formato `.zip` con los trabajos de los estudiantes.
* **Formatos Soportados:** Procesamiento automático de documentos en formato `.pdf` y `.docx` (Word).
* **Evaluación Inteligente (Gemini API):** 
  * Extracción automática del nombre del alumno directamente desde su archivo de entrega.
  * Calificación objetiva adaptada estrictamente a las rúbricas y pesos configurados por el docente.
* **Configuración del Modelo de IA:**
  * Creación y edición de rúbricas personalizadas con asignación de puntajes (pesos).
  * Carga de un **Documento de Guía** (pauta de corrección) para orientar el criterio de la inteligencia artificial.
* **Gestión de Resultados:**
  * Buscador avanzado de alumnos por nombre o por tarea específica.
  * **Retroalimentación automatizada:** Generación de comentarios detallados sobre aciertos y puntos de mejora para cada estudiante.
  * **Exportación de Datos:** Descarga de reportes de calificaciones directamente a formato **Excel**.

## Tecnologías Utilizadas

* **Backend / Core:** HTML / Python 
* **Inteligencia Artificial:** Google Gemini API
* **Base de Datos:** MySQL
* **Formatos de Exportación:** Microsoft Excel

## 📋 Requisitos Previos

Antes de ejecutar el proyecto, asegúrate de contar con:
1. Un servidor local instalado (Laragon, etc.).
2. Una clave de API activa de **Google Gemini**.
