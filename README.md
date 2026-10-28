

\# NGO Donation, Volunteer \& Community Project Management System



A FastAPI backend for managing NGO donors, donations, fundraising campaigns, volunteers, projects, budgets, expenses, beneficiaries, inventory, notifications, receipts, reports, and audit logs.



\## Features



\- User authentication and role-based authorization

\- Donor and donation management

\- Fundraising campaigns

\- Volunteer registration and assignments

\- NGO projects, tasks, milestones, and approvals

\- Expense and budget management

\- Resource inventory and inventory movements

\- Beneficiary and impact tracking

\- Notifications and donation receipts

\- Dashboard analytics and reports

\- CSV reporting

\- Audit logging

\- Business-rule validation

\- Automated tests

\- SQLAlchemy database models and Alembic migrations

\- Docker deployment configuration



\## Technology Stack



\- Python 3.11+

\- FastAPI

\- Pydantic and Pydantic Settings

\- SQLAlchemy

\- SQLite

\- Alembic

\- JWT authentication

\- Pytest

\- Docker and Docker Compose



\## Requirements



For local development:



\- Python 3.11 or later

\- pip

\- Git (optional)



For container deployment:



\- Docker

\- Docker Compose



\## Local Installation — Windows PowerShell



\### 1. Open the project directory



```powershell

cd C:\\Users\\admin\\ngo-management-system

```



\### 2. Create a virtual environment



```powershell

python -m venv .venv

```



\### 3. Activate the environment



```powershell

.\\.venv\\Scripts\\Activate.ps1

```



\### 4. Install dependencies



```powershell

python -m pip install -r requirements.txt

```



\### 5. Configure environment variables



Copy the example file:



```powershell

Copy-Item .env.example .env

```



Edit `.env` and replace the example secret with a strong, randomly generated secret.



Do not commit `.env` or share its contents.



\### 6. Apply database migrations



```powershell

python -m alembic upgrade head

```



\*\*Existing database warning:\*\* If you already have a populated database created before Alembic was introduced, back it up and follow a database baselining procedure before applying the initial migration. Do not apply the initial migration directly to an existing database containing these tables.



\### 7. Start the application



```powershell

python -m uvicorn app.main:app --reload

```



The local API is available at:



\- API root: http://127.0.0.1:8000/

\- Health endpoint: http://127.0.0.1:8000/health

\- Interactive API documentation: http://127.0.0.1:8000/docs

\- Alternative API documentation: http://127.0.0.1:8000/redoc



\## Running Tests



Run the complete test suite:



```powershell

python -m pytest -q

```



Run tests with code coverage:



```powershell

python -m pytest --cov=app --cov-report=term-missing

```



Compile the application and tests:



```powershell

python -m compileall app tests

```



Latest recorded verification before deployment configuration:



\- 303 tests passed

\- 0 failed tests

\- 89% code coverage

\- One Starlette deprecation warning



Run these checks again after any code or dependency changes.



\## Database Migrations



Check the current revision:



```powershell

python -m alembic current

```



Apply pending migrations:



```powershell

python -m alembic upgrade head

```



Check whether model changes require a migration:



```powershell

python -m alembic check

```



Generate a migration after changing SQLAlchemy models:



```powershell

python -m alembic revision --autogenerate -m "describe your schema change"

```



Review every generated migration before applying it.



Back up important databases before running migrations. Migration scripts should be committed to version control.



\## Docker Deployment



Build and start the application:



```powershell

docker compose up --build -d

```



Set the production secret in the PowerShell session before running Compose:



```powershell

$env:SECRET\_KEY = "replace-with-a-long-random-secret"

```



For production, generate a strong random secret and keep it in a secure secret manager rather than storing it in source control.



View application logs:



```powershell

docker compose logs -f api

```



Stop the application:



```powershell

docker compose down

```



The Compose configuration uses a named Docker volume for the SQLite database. Stopping the container does not normally remove this volume.



Do not use `docker compose down -v` unless you intentionally want to remove the database volume and its data.



\## Health Checks



Check the health endpoint after starting the application:



```powershell

Invoke-RestMethod http://127.0.0.1:8000/health

```



Expected response:



```json

{

&#x20; "status": "healthy"

}

```



\## Security Notes



\- Never commit `.env`, passwords, API tokens, or production secrets.

\- Use a strong, unique secret key in production.

\- Use HTTPS when exposing the API publicly.

\- Back up the database and test restoring backups.

\- Review authorization rules before public deployment.

\- Configure production logging and monitoring.

\- Use a managed production database for larger or concurrent workloads.

\- Review generated database migrations before deployment.

\- Do not expose the development server with `--reload` in production.



\## Project Structure



```text

ngo-management-system/

├── app/

│   ├── api/

│   ├── core/

│   ├── db/

│   ├── models/

│   ├── schemas/

│   ├── services/

│   └── main.py

├── alembic/

│   ├── versions/

│   └── env.py

├── tests/

├── .dockerignore

├── .env.example

├── .gitignore

├── alembic.ini

├── Dockerfile

├── docker-compose.yml

├── requirements.txt

└── README.md

```



\## Current Status



The core application and its automated tests have been implemented.



The initial Alembic migration has been generated and verified against a temporary, empty SQLite database. The existing application test suite last reported 303 passing tests.



Docker image building, container startup, and deployment to a real server must be verified separately before considering production deployment complete.



