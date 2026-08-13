# Guía rápida de publicación

## Lo que necesitarás

- Tu cuenta de GitHub.
- Una cuenta gratuita de Supabase.
- Una cuenta gratuita de Streamlit Community Cloud vinculada a GitHub.

## Orden recomendado

1. Crea en GitHub un repositorio **privado** llamado `presupuesto-familiar`.
2. Descomprime el ZIP y sube todos sus archivos al repositorio.
3. Crea el proyecto de Supabase.
4. Ejecuta `sql/schema.sql` desde el SQL Editor de Supabase.
5. Crea la app en Streamlit Community Cloud seleccionando ese repositorio y `app.py`.
6. En los secretos de Streamlit agrega `APP_PASSWORD`, `SUPABASE_URL` y `SUPABASE_KEY`.
7. Publica, entra con tu contraseña y prueba una importación de Alzex.

## Importante

- No subas `.streamlit/secrets.toml` a GitHub.
- No publiques el repositorio: contiene tus archivos financieros iniciales.
- Usa la clave `service_role` de Supabase únicamente en los secretos de Streamlit.
- Cuando la nueva dirección funcione, la versión alojada en `chatgpt.site` se puede eliminar.
