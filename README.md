# Presupuesto Familiar

Aplicación privada e independiente para analizar movimientos exportados desde Alzex, comparar gasto real contra presupuesto, identificar tendencias y registrar inversiones.

## Arquitectura

- Python + Streamlit
- Supabase (PostgreSQL) para persistencia
- Plotly para visualizaciones
- Contraseña propia guardada como secreto del despliegue
- Sin servicios, login ni código de ChatGPT/OpenAI

## 1. Crear el repositorio privado en GitHub

1. En GitHub selecciona **New repository**.
2. Nombre sugerido: `presupuesto-familiar`.
3. Marca **Private** y créalo vacío.
4. Selecciona **Add file → Upload files** y sube el contenido de esta carpeta (no la carpeta contenedora).
5. Confirma con **Commit changes**.

## 2. Crear Supabase

1. Crea un proyecto en https://supabase.com/.
2. Abre **SQL Editor**, pega el contenido de `sql/schema.sql` y ejecútalo.
3. En **Project Settings → API**, copia `Project URL` y la clave `service_role`.

La clave `service_role` debe guardarse únicamente en los secretos privados de Streamlit. No la subas a GitHub ni la pegues en archivos del repositorio. Las tablas mantienen RLS activo y no permiten acceso público directo.

## 3. Publicar en Streamlit Community Cloud

1. Entra a https://share.streamlit.io/ con tu cuenta de GitHub.
2. Selecciona **Create app** y el repositorio privado.
3. Archivo principal: `app.py`.
4. En **Advanced settings → Secrets**, pega:

```toml
APP_PASSWORD = "TU CONTRASEÑA"
SUPABASE_URL = "https://TU-PROYECTO.supabase.co"
SUPABASE_KEY = "TU-CLAVE-SERVICE-ROLE"
```

5. Publica la aplicación. La contraseña nunca debe subirse a GitHub.

## Uso mensual

1. Exporta el CSV desde Alzex.
2. Abre **Importar Alzex**.
3. Revisa movimientos nuevos y duplicados.
4. Confirma la importación.

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
streamlit run app.py
```

## Datos incluidos

Los archivos en `data/initial/` sirven como punto de partida. Como contienen información financiera, conserva el repositorio como **privado**.
