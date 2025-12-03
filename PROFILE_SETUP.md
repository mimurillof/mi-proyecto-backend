# Configuración de Perfil de Usuario en Supabase

## 1. Agregar Nuevas Columnas a la Tabla `users`

Ejecuta el siguiente SQL en el Editor SQL de Supabase:

```sql
-- ============================================================
-- SQL PARA AGREGAR COLUMNAS DE PERFIL A LA TABLA USERS
-- Ejecutar en Supabase SQL Editor
-- ============================================================

-- Agregar columnas adicionales para el perfil de usuario
ALTER TABLE public.users 
ADD COLUMN IF NOT EXISTS mobile VARCHAR(20),
ADD COLUMN IF NOT EXISTS country VARCHAR(100),
ADD COLUMN IF NOT EXISTS identification_number VARCHAR(50),
ADD COLUMN IF NOT EXISTS bio TEXT,
ADD COLUMN IF NOT EXISTS profile_image_path VARCHAR(500);

-- Comentarios descriptivos para las columnas
COMMENT ON COLUMN public.users.mobile IS 'Número de teléfono móvil del usuario';
COMMENT ON COLUMN public.users.country IS 'País de residencia del usuario';
COMMENT ON COLUMN public.users.identification_number IS 'Número de identificación (cédula, DNI, pasaporte, etc.)';
COMMENT ON COLUMN public.users.bio IS 'Biografía o descripción personal del usuario';
COMMENT ON COLUMN public.users.profile_image_path IS 'Path de la imagen de perfil en Supabase Storage (bucket portfolio-files)';

-- Verificar que las columnas se crearon correctamente
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN ('mobile', 'country', 'identification_number', 'bio', 'profile_image_path');
```

## 2. Estructura de Almacenamiento de Imágenes

Las imágenes de perfil se almacenan en el bucket existente `portfolio-files`:

```
portfolio-files/
├── {user_id}/
│   ├── profile.jpg          # Imagen de perfil del usuario
│   ├── api_response_B.json   # Datos del portfolio (existente)
│   └── ... otros archivos
```

**No se requiere crear un nuevo bucket.** La imagen de perfil se guarda en la carpeta del usuario dentro de `portfolio-files`.

## 3. Endpoints Disponibles

Una vez configurado, tendrás los siguientes endpoints:

### Obtener Perfil Completo
```
GET /api/users/profile
Authorization: Bearer <token>
```

Respuesta:
```json
{
  "user_id": "uuid",
  "email": "usuario@email.com",
  "first_name": "Miguel Ángel",
  "last_name": "Murillo",
  "birth_date": "1990-01-15",
  "gender": "male",
  "mobile": "+57 300 123 4567",
  "country": "Colombia",
  "identification_number": "1020XXXXXX",
  "bio": "Estudiante de Ciencia de Datos...",
  "profile_image_url": "https://supabase.../signed-url",
  "created_at": "2024-01-01T00:00:00Z",
  "has_completed_onboarding": true
}
```

### Actualizar Perfil
```
PUT /api/users/profile
Authorization: Bearer <token>
Content-Type: application/json

{
  "first_name": "Miguel",
  "last_name": "Murillo",
  "mobile": "+57 300 123 4567",
  "country": "Colombia",
  "identification_number": "1020XXXXXX",
  "bio": "Mi nueva biografía...",
  "gender": "male",
  "birth_date": "1990-01-15"
}
```

### Obtener Solo Avatar
```
GET /api/users/profile/avatar
Authorization: Bearer <token>
```

Respuesta:
```json
{
  "avatar_url": "https://...",
  "is_default": false,
  "gender": "male"
}
```

### Subir Imagen de Perfil
```
POST /api/users/profile/avatar
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <imagen>
```

### Eliminar Imagen de Perfil
```
DELETE /api/users/profile/avatar
Authorization: Bearer <token>
```

## 4. Avatares por Defecto

Si el usuario no tiene imagen de perfil, el sistema retorna un avatar generado automáticamente:

- **Masculino**: Avatar estilo persona con fondo azul claro
- **Femenino**: Avatar estilo persona con fondo naranja claro
- **Otro**: Avatar neutral con fondo morado claro
- **Prefiere no decir / Sin género**: Avatar con iniciales del nombre

Los avatares se generan usando [DiceBear Avatars](https://www.dicebear.com/).

## 5. Integración en Frontend

### Para la página de Perfil:
```typescript
// Obtener perfil completo
const response = await fetch('/api/users/profile', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const profile = await response.json();

// Usar profile.profile_image_url para la imagen
// Usar profile.first_name, profile.last_name, etc. para los datos
```

### Para la barra superior (navbar):
```typescript
// Obtener solo el avatar (más ligero)
const response = await fetch('/api/users/profile/avatar', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { avatar_url, is_default } = await response.json();

// Usar avatar_url para el <img> del navbar
```

### Para subir nueva imagen:
```typescript
const formData = new FormData();
formData.append('file', selectedFile);

const response = await fetch('/api/users/profile/avatar', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: formData
});
```
