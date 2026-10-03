from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    """docstring for root"""
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


class A:
    x = 1