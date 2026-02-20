# VeridisClip

VeridisClip es un sistema independiente de clipeo de video con IA, extraído de la integración previa en Veridis y preparado para funcionar como servicio modular.

## Contexto del proyecto
- Origen: fork/evolución práctica de AutoClip, separado para operar como producto propio.
- Objetivo: generar clips y colecciones desde videos (archivo, YouTube, Facebook, Bilibili) con pipeline de IA.
- Dirección técnica: arquitectura modular para que Veridis (u otros sistemas) lo consuman como módulo desacoplado.

## Estado actual
- Repo independiente: `https://github.com/642studio/VeridisClip.git`
- Backend y frontend desacoplados de `veridis/web`.
- Flujo operativo:
  1. Importación/descarga de video
  2. Subtítulos (existente o ASR)
  3. Outline (LLM)
  4. Timeline
  5. Scoring
  6. Generación de clips y colecciones
- Integración de progreso unificada:
  - Barra de importación/descarga
  - Transición a procesamiento
  - Manejo de fallback cuando faltan eventos de progreso fino

## Arquitectura
- `backend/`: FastAPI + Celery + Redis + SQLite
- `frontend/`: React + Vite + Ant Design
- `backend/modules/clipping/`: base modular de dominio/aplicación/infra para el clipeo
- `data/`: estado local de ejecución (DB, proyectos, metadata, outputs)

## Estructura clave
- `backend/api/v1/`: endpoints de proyectos, clips, colecciones, settings, youtube/bilibili
- `backend/services/`: orquestación y servicios de negocio
- `backend/pipeline/`: pasos del pipeline
- `backend/tasks/`: tareas Celery
- `frontend/src/pages/`: Home, ProjectDetail, Settings
- `frontend/src/components/`: UI de importación, estado y gestión de clips/colecciones

## Requisitos
- Python 3.9+
- Node 18+
- Redis local (`localhost:6379`)
- ffmpeg instalado

## Configuración local
1. Clonar repo
```bash
git clone https://github.com/642studio/VeridisClip.git
cd VeridisClip
```

2. Backend
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Frontend
```bash
cd frontend
npm install
cd ..
```

4. Variables de entorno
- Crear `.env` en raíz (backend) con base en `env.example`.
- Configurar proveedor LLM/API key desde `.env` o desde UI de settings.

## Arranque (modo desarrollo)

### Opción A: manual (recomendado para debug)
Terminal 1 (backend API):
```bash
cd /ruta/VeridisClip
source venv/bin/activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Terminal 2 (worker Celery):
```bash
cd /ruta/VeridisClip
source venv/bin/activate
./venv/bin/celery -A backend.core.celery_app:celery_app worker \
  --loglevel=info --pool=solo \
  -Q processing,video,notification,upload,celery
```

Terminal 3 (frontend):
```bash
cd /ruta/VeridisClip/frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

### Opción B: scripts legacy del proyecto
- `start_autoclip.sh`
- `stop_autoclip.sh`
- `status_autoclip.sh`

## URLs
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`

## Flujo funcional esperado
1. Crear/importar proyecto por archivo o link.
2. Ver progreso de importación/descarga.
3. Inicio automático de pipeline.
4. Al finalizar, ver clips y colecciones en detalle del proyecto.

## Consideraciones operativas importantes
- Si el worker Celery escucha solo cola `celery`, el pipeline puede quedar en estado “running fantasma”.
  - Debe escuchar también: `processing,video,notification,upload`.
- Los endpoints de logs en algunos casos son estáticos/demo y no reflejan todo el runtime real.
- El scoring/LLM puede devolver respuestas vacías o topar límites (`429`), afectando cantidad/calidad de clips.

## Troubleshooting rápido

### “Proyecto en processing pero no avanza”
- Verificar worker y colas:
```bash
./venv/bin/celery -A backend.core.celery_app:celery_app inspect active
./venv/bin/celery -A backend.core.celery_app:celery_app inspect reserved
```

### “Barra en 0% aunque hay carga de CPU”
- Confirmar datos del proyecto:
```bash
curl -s http://localhost:8000/api/v1/projects/<project_id> | jq .
```
- Revisar `settings.download_progress` y `settings.download_message`.

### “No se generaron clips”
- Revisar metadata:
  - `data/projects/<project_id>/metadata/step2_timeline.json`
  - `data/projects/<project_id>/metadata/step3_high_score_clips.json`
- Si hay clips en DB pero no en UI, recargar detalle/proyecto y validar endpoints `clips`.

## Separación Veridis vs VeridisClip
- VeridisClip ya no depende del monorepo `Veridis` para ejecutar backend/frontend.
- La integración con Veridis debe hacerse vía API (módulo externo), no por acoplamiento de código interno.

## Roadmap inmediato
- Limpiar artefactos heredados de AutoClip en naming/documentación/scripts.
- Endurecer observabilidad real (logs por proyecto/tarea y trazas de pipeline).
- Mejorar fallback cuando LLM devuelve vacío para evitar proyectos “completados sin valor”.
- Publicar contrato API estable para integración modular con Veridis.

## Seguridad
- Nunca subir API keys reales al repo.
- Usar `.env` local y rotar claves si alguna fue expuesta.

## Licencia
MIT (heredada del proyecto base).
