from fastapi import APIRouter, Depends, Path, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse

from models import Base, Todo
from database import engine, SessionLocal
from typing import Annotated
from routers.auth import get_current_user
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/todo", tags=["Todo"])

templates = Jinja2Templates(directory="templates")


class TodoRequest(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=3, max_length=1000)
    priority: int = Field(gt=0, lt=6)
    completed: bool = False


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def redirect_to_login():
    redirect_response = RedirectResponse(url="/auth/login-page", status_code=status.HTTP_302_FOUND)
    redirect_response.delete_cookie("access_token")
    return redirect_response


@router.get("/todo-page")
async def render_todo_page(request: Request, db: db_dependency):
    try:
        user = await get_current_user(request.cookies.get("access_token"))
        if user is None:
            return redirect_to_login()
        todos = db.query(Todo).filter(Todo.owner_id == user.get("user_id")).all()
        return templates.TemplateResponse("todo.html", {"request": request, "todos": todos, "user": user})
    except:
        return redirect_to_login()


@router.get("/add-todo-page")
async def render_add_todo_page(request: Request):
    try:
        user = await get_current_user(request.cookies.get("access_token"))
        if user is None:
            return redirect_to_login()
        return templates.TemplateResponse("add-todo.html", {"request": request, "user": user})

    except:
        return redirect_to_login()


@router.get("/edit-todo-page/{todo_id}")
async def render_todo_page(request: Request, todo_id: int, db: db_dependency):
    try:
        user = await get_current_user(request.cookies.get("access_token"))
        if user is None:
            return redirect_to_login()
        todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get("user_id")).first()
        return templates.TemplateResponse("edit-todo.html", {"request": request, "todo": todo, "user": user})
    except Exception as e:
        return redirect_to_login()


@router.get("/get_all")
async def read_all(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return db.query(Todo).filter(Todo.owner_id == user.get("user_id")).all()


@router.get("/todo/{todo_id}", status_code=status.HTTP_200_OK)
async def read_by_id(user: user_dependency,db: db_dependency, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get("user_id")).first()
    if todo is not None:
        return todo
    raise HTTPException(status_code=404, detail="Todo not found")


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_todo(user: user_dependency, todo_request: TodoRequest, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    todo = Todo(**todo_request.model_dump(), owner_id=user.get("user_id"))
    db.add(todo)
    db.commit()


@router.put("/update/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(user: user_dependency, todo_request: TodoRequest, db: db_dependency, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get("user_id")).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")

    todo.completed = todo_request.completed
    todo.priority = todo_request.priority
    todo.title = todo_request.title
    todo.description = todo_request.description

    db.add(todo)
    db.commit()


@router.delete("/delete/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    todo = db.query(Todo).filter(Todo.id == todo_id).filter(Todo.owner_id == user.get("user_id")).first()

    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    db.delete(todo)
    db.commit()
