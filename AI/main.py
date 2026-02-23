import uvicorn
from fastapi import FastAPI

from AI.routers import all_AI_routers

app = FastAPI(
    title="AI-bot",
    description="AI-bot",
)

all_routers = [
    *all_AI_routers
]

for router in all_routers:
    app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
