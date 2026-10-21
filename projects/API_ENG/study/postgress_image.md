docker run --name api-postgres -e POSTGRES_USER=api_user -e POSTGRES_PASSWORD=dev_password -e POSTGRES_DB=api_db -p 5432:5432 -v api_postgres_data:/var/lib/postgresql -d postgres:18



Next: Verify PostgreSQL is running
1. Check container status
docker ps


You should see api-postgres with a status of Up.
2. Check PostgreSQL logs
docker logs api-postgres


Look for:
database system is ready to accept connections


3. Connect to PostgreSQL inside the container
docker exec -it api-postgres psql -U api_user -d api_db


If successful, you'll see:
api_db=#


You can now execute SQL:
SELECT version();


Exit with \q.
Your FastAPI connection string
When running FastAPI directly on Windows:
DATABASE_URL = "postgresql://api_user:dev_password@localhost:5432/api_db"



This will be your connection string for SQLAlchemy or another PostgreSQL client.
One important detail: Your volume path /var/lib/postgresql is correct for the official PostgreSQL 18 Docker image, which uses a version-specific data directory.
Your next step is to verify docker ps and then test the database connection.

### DBWeaver 
Connect using:
Setting	Value
Host	localhost
Port	5432
Database	api_db
Username	api_user
Password	dev_password

### 2. Configure your project
After installation, you'll need to:
- Create your FastAPI application and API routers.
- Configure the PostgreSQL connection using SQLAlchemy.
- Create a .env file for database credentials.
- Initialize Alembic for database migrations.
- Create Pydantic schemas for request and response validation.
- Configure pytest for automated tests.
- Add .venv, .env and other generated files to .gitignore.

### 3. Verify FastAPI
Create main.py:
```python
from fastapi import FastAPI

app = FastAPI(title="Backend API Project")

@app.get("/health")
def health():
    return {"status": "ok"}
```
Start your server:

 ``fastapi dev main.py``
