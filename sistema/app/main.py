from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .acesso import permitido, recurso_da_rota
from .atividade import registrar
from .database import Base, SessionLocal, engine, migrar
from .feriados import sincronizar_feriados
from .gestao_routes import router as gestao_router
from .plataforma_routes import router as plataforma_router
from .routes import router
from .rules import RegraNegocio
from .seed import seed_if_empty

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    migrar()
    db = SessionLocal()
    try:
        await sincronizar_feriados(db)
        seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Rotina em ordem", lifespan=lifespan)
app.include_router(router)
app.include_router(gestao_router)
app.include_router(plataforma_router)
uploads = Path(__file__).resolve().parent.parent / "uploads"
uploads.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads), name="uploads")
def _pasta_videos() -> Path | None:
    candidatos = [
        Path(__file__).resolve().parents[2] / "site" / "videos",
        DIST / "videos",
    ]
    for pasta in candidatos:
        if pasta.is_dir() and any(pasta.iterdir()):
            return pasta
    return None


videos = _pasta_videos()
if videos is not None:
    app.mount("/videos", StaticFiles(directory=videos), name="videos")


@app.middleware("http")
async def exigir_acesso(request: Request, call_next):
    recurso = recurso_da_rota(request.url.path)
    if recurso:
        from .models import Sessao, Usuario

        db = SessionLocal()
        try:
            token = request.cookies.get("sessao")
            sessao = db.get(Sessao, token) if token else None
            usuario = db.get(Usuario, sessao.usuario_id) if sessao and sessao.expira_em >= datetime.now() else None
            negado = usuario is not None and not permitido(usuario.papel, recurso)
        finally:
            db.close()
        if negado:
            return JSONResponse(status_code=403, content={"detail": {"mensagem": "Seu cargo não abre essa área."}})
    return await call_next(request)


@app.middleware("http")
async def guardar_atividade(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api") and response.status_code < 400:
        try:
            registrar(request.cookies.get("sessao"), request.method, request.url.path)
        except Exception:
            pass
    return response


@app.exception_handler(RegraNegocio)
async def regra_negocio(_, erro: RegraNegocio):
    return JSONResponse(status_code=erro.status, content={"detail": {"mensagem": erro.mensagem, **erro.extra}})


def _arquivo_frontend(caminho: str):
    if not caminho or caminho.endswith("/"):
        return None
    alvo = (DIST / caminho).resolve()
    raiz = DIST.resolve()
    if alvo.is_file() and (alvo == raiz or raiz in alvo.parents):
        return FileResponse(alvo)
    return None


@app.get("/")
def inicio():
    index = DIST / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"api": "/docs", "frontend": "http://127.0.0.1:5173"}


@app.get("/{caminho:path}")
def frontend(caminho: str):
    arquivo = _arquivo_frontend(caminho)
    if arquivo is not None:
        return arquivo
    index = DIST / "index.html"
    if index.is_file() and not caminho.startswith("api"):
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Não encontrado.")
