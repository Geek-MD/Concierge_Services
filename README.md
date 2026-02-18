[![Geek-MD - Concierge Services](https://img.shields.io/static/v1?label=Geek-MD&message=Concierge%20Services&color=blue&logo=github)](https://github.com/Geek-MD/Concierge_Services)
[![Stars](https://img.shields.io/github/stars/Geek-MD/Concierge_Services?style=social)](https://github.com/Geek-MD/Concierge_Services)
[![Forks](https://img.shields.io/github/forks/Geek-MD/Concierge_Services?style=social)](https://github.com/Geek-MD/Concierge_Services)

[![GitHub Release](https://img.shields.io/github/release/Geek-MD/Concierge_Services?include_prereleases&sort=semver&color=blue)](https://github.com/Geek-MD/Concierge_Services/releases)
[![License](https://img.shields.io/badge/License-MIT-blue)](https://github.com/Geek-MD/Concierge_Services/blob/main/LICENSE)
[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom%20Repository-blue)](https://hacs.xyz/)

# Concierge Services

**Concierge Services** es una integración personalizada para [Home Assistant](https://www.home-assistant.io) que te permite gestionar facturas de servicios (electricidad, agua, gas, etc.) recibidas por correo electrónico. La integración extrae automáticamente información de los PDFs adjuntos y crea sensores para cada servicio con el total a pagar y datos adicionales.

---

## ✨ Características

- 📧 **Configuración de correo IMAP**: Conecta tu cuenta de correo donde recibes las facturas de servicios
- ✅ **Validación de credenciales**: Verifica automáticamente que las credenciales IMAP sean correctas
- 🔒 **Almacenamiento seguro**: Las credenciales se guardan de forma segura en Home Assistant
- 🌐 **Soporte multiidioma**: Interfaz completa en español e inglés
- 🎯 **Configuración por UI**: No requiere edición de archivos YAML

### 🚧 Próximamente

- 📊 **Sensores por servicio**: Configura sensores individuales para cada servicio (electricidad, agua, gas, etc.)
- 📄 **Extracción de PDFs**: Analiza automáticamente los PDFs de las facturas
- 💰 **Total a pagar**: El sensor muestra el monto total a pagar
- 📈 **Atributos detallados**: Consumo, número de cliente, período y otros datos como atributos del sensor
- 🔔 **Notificaciones**: Alertas cuando llega una nueva factura

---

## 📦 Instalación

### Opción 1: HACS (Recomendado)

1. Abre HACS en Home Assistant
2. Ve a **Integraciones → Repositorios Personalizados**
3. Agrega este repositorio:
   ```
   https://github.com/Geek-MD/Concierge_Services
   ```
   Selecciona tipo: **Integration**
4. Instala y reinicia Home Assistant
5. Ve a **Configuración → Dispositivos y Servicios → Agregar Integración** y selecciona **Concierge Services**

---

### Opción 2: Instalación Manual

1. Descarga este repositorio
2. Copia la carpeta `custom_components/concierge_services/` en el directorio `config/custom_components/` de tu Home Assistant
3. Reinicia Home Assistant
4. Agrega la integración mediante la UI

---

## ⚙️ Configuración

Toda la configuración se realiza a través de la interfaz de usuario.

1. Ve a **Configuración** → **Dispositivos y Servicios**
2. Haz clic en el botón **+ Agregar Integración**
3. Busca **Concierge Services**
4. Ingresa los datos de tu cuenta de correo:
   - **Servidor IMAP**: El servidor de correo IMAP
   - **Puerto IMAP**: El puerto IMAP (por defecto: `993`)
   - **Correo Electrónico**: Tu dirección de correo
   - **Contraseña**: Tu contraseña o contraseña de aplicación

### Ejemplos de Configuración

#### Gmail
- **Servidor IMAP**: `imap.gmail.com`
- **Puerto IMAP**: `993`
- **Correo**: `tucorreo@gmail.com`
- **Contraseña**: Usa una [contraseña de aplicación](https://support.google.com/accounts/answer/185833)

#### Outlook/Hotmail
- **Servidor IMAP**: `outlook.office365.com`
- **Puerto IMAP**: `993`
- **Correo**: `tucorreo@outlook.com`
- **Contraseña**: Tu contraseña de cuenta

#### Yahoo Mail
- **Servidor IMAP**: `imap.mail.yahoo.com`
- **Puerto IMAP**: `993`
- **Correo**: `tucorreo@yahoo.com`
- **Contraseña**: Usa una [contraseña de aplicación](https://help.yahoo.com/kb/generate-manage-third-party-passwords-sln15241.html)

---

## 🚀 Estado del Desarrollo

### ✅ Fase 1: Configuración de Credenciales (Completada)
- Configuración de cuenta IMAP mediante UI
- Validación de credenciales en tiempo real
- Almacenamiento seguro de credenciales
- Interfaz en español e inglés
- Compatibilidad con HACS

### 🔜 Próximas Fases

#### Fase 2: Creación de Sensores
- Configurar sensores individuales por servicio
- Especificar nombre del servicio (ej: "Electricidad", "Agua", "Gas")
- Definir campos del PDF a extraer

#### Fase 3: Lectura de Correos
- Conectar al servidor IMAP configurado
- Filtrar correos de cuentas de servicio
- Descargar archivos PDF adjuntos
- Identificar nuevas facturas

#### Fase 4: Extracción de Datos
- Analizar PDFs con OCR/parsing
- Extraer información configurable:
  - Número de cliente
  - Período de facturación
  - Consumo
  - Total a pagar
  - Fecha de vencimiento

#### Fase 5: Actualización de Sensores
- Actualizar estado del sensor con total a pagar
- Guardar datos adicionales como atributos
- Disparar eventos cuando llega nueva factura
- Historial de facturas anteriores

---

## 📓 Notas

- La integración actualmente solo configura las credenciales IMAP
- Las fases siguientes agregarán la funcionalidad de sensores y lectura de correos
- Todas las credenciales se almacenan de forma segura en Home Assistant
- Se recomienda usar contraseñas de aplicación en lugar de la contraseña principal

---

## 🙋‍♂️ Soporte

Si encuentras algún problema o tienes sugerencias, por favor [abre un issue](https://github.com/Geek-MD/Concierge_Services/issues).

---

## 📄 Licencia

MIT © Edison Montes [_@GeekMD_](https://github.com/Geek-MD)

---

<div align="center">
  
💻 **Proudly developed with GitHub Copilot** 🚀

</div>