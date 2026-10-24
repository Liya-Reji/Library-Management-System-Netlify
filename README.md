# Library Management System

A beginner-friendly, production-ready **Library Management System** web application developed with Python Flask, PostgreSQL, Bootstrap 5, Docker, Kubernetes (Minikube), and Render cloud hosting. This project is specifically designed to demonstrate end-to-end full-stack web development, containerization, orchestration, and continuous cloud deployment for college microprojects and BCA/B.Tech evaluations.

---

## 1. Project Overview & Objectives

The primary objective of this system is to streamline academic library operations by automating catalog tracking, student record management, book issue/return workflows, and inventory protection through ACID transactions.

### Core Objectives:
- **Librarian Administration:** Centralized control over book inventory, student registration, issue/return transactions, and overdue monitoring.
- **Student Portal:** Self-service catalog discovery, real-time availability checks, personal loan status, and borrow history.
- **Microproject Demonstration:** Showcases modern DevOps best practices: Docker multi-stage containerization, local Kubernetes orchestration via Minikube on Windows 11, and production cloud hosting on Render.

---

## 2. Architecture Diagram

```mermaid
flowchart TD
    subgraph Client["Client Browser"]
        Librarian["Librarian / Admin Portal"]
        StudentUser["Student Portal"]
    end

    subgraph AppServer["Flask Web Application (Gunicorn)"]
        Routes["Blueprints (Auth, Admin, Student, Public)"]
        Security["Session Auth & CSRF Middleware"]
        ORM["SQLAlchemy ORM & Models"]
    end

    subgraph DataLayer["Relational Database"]
        PostgresDB[("PostgreSQL 16 (Docker / K8s / Render)")]
        SQLiteLocal[("SQLite Fallback (Local Dev)")]
    end

    subgraph DeployEnv["Deployment Targets"]
        LocalCompose["Docker Compose (App + Postgres Container)"]
        K8sCluster["Kubernetes / Minikube (Pods, PVC, Services)"]
        RenderCloud["Render PaaS (Web Service + Managed DB)"]
    end

    Client -->|HTTPS / HTTP| Routes
    Routes --> Security
    Security --> ORM
    ORM --> PostgresDB
    ORM -.-> SQLiteLocal

    AppServer --> LocalCompose
    AppServer --> K8sCluster
    AppServer --> RenderCloud
```

---

## 3. Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons |
| **Backend** | Python 3.12+, Flask 3.1, Werkzeug 3.1 (Password Hashing) |
| **Database** | PostgreSQL 16 (Production/Docker/Render), SQLite 3 (Local testing) |
| **ORM** | Flask-SQLAlchemy 3.1 & SQLAlchemy 2.0 |
| **Application Server**| Gunicorn 23.0 WSGI Server |
| **Containerization**| Docker & Docker Compose |
| **Orchestration** | Kubernetes 1.30+ with Minikube on Windows 11 |
| **Cloud Hosting** | Render (Managed Web Service & PostgreSQL Database) |
| **Testing** | Python `unittest` test suite (23 automated test cases) |
| **Version Control** | Git & GitHub |

---

## 4. Features & User Roles

### 🧑‍💼 Administrator / Librarian Role
- **Dashboard Statistics:** View live totals for books, available copies, issued copies, registered students, and overdue alerts.
- **Book Catalog Management:** Add, edit, search (title, author, category, ISBN), and delete books. Strict validation prevents available copies from exceeding total copies.
- **Student Management:** Register students, update details, search profiles by roll number or email, and view active borrow tallies.
- **Circulation & Transactions:**
  - Issue available books with configurable return due dates (default: 14 days).
  - Automatically decrement available copy counts upon issue.
  - Automatically increment copy counts upon book return (capped at total owned).
  - Prevent duplicate returns and reject issue requests when zero copies are available.
  - Track overdue loans with visual overdue flags.
- **Audit History:** Comprehensive archive of all past and current borrowing records with multi-criteria filtering.

### 🎓 Student Role
- **Registration & Authentication:** Secure student registration and login with password hashing.
- **Catalog Exploration:** Search and browse all library books with live stock status (`Available` or `Checked Out`).
- **Student Dashboard:** View currently borrowed books, remaining days before due date, and overdue notices.
- **Borrowing History:** Personal record of all returned and active books.
- **Role Isolation:** Strict server-side route guards (HTTP 403 Forbidden) prevent students from accessing administrative pages.

---

## 5. Prerequisites for Windows 11

Before running or deploying the project, ensure the following software is installed on Windows 11:
1. **Python 3.11 or 3.12:** [Download from python.org](https://www.python.org/downloads/) (Check *"Add python.exe to PATH"* during install).
2. **Git for Windows:** [Download from git-scm.com](https://git-scm.com/).
3. **Docker Desktop:** [Download Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) (Enable WSL 2 backend).
4. **Minikube & kubectl:** Installed via Windows Package Manager (`winget install Kubernetes.minikube Kubernetes.kubectl`).

---

## 6. Local Setup & Execution (Without Docker)

### Step 1: Open PowerShell and navigate to the project directory
```powershell
cd "d:\Library Management System"
```

### Step 2: Create and activate a Python virtual environment (Optional but Recommended)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure environment variables
Copy the provided template:
```powershell
Copy-Item .env.example .env
```

### Step 5: Initialize database and populate demo data
```powershell
python scripts/init_db.py
python scripts/seed_data.py
```

### Step 6: Start the Flask development server
```powershell
python app.py
```
Open your browser at `http://localhost:5000`.

### Default Demo Credentials:
- **Librarian Account:** `admin` | Password: `admin123`
- **Student Account:** `student1` | Password: `student123`

---

## 7. Docker & Docker Compose Deployment

Docker Compose starts both the Flask web application (running Gunicorn) and an isolated PostgreSQL 16 database with a named persistent volume.

### Step 1: Start Docker Desktop on Windows 11
Make sure Docker Desktop is launched and shows "Engine running".

### Step 2: Build and run the containers
```powershell
docker compose up --build
```
To run in background (detached mode):
```powershell
docker compose up --build -d
```

### Step 3: Initialize and seed demo data inside the container
In a new PowerShell terminal, run:
```powershell
docker compose exec web python scripts/init_db.py
docker compose exec web python scripts/seed_data.py
```

### Step 4: Inspect container status and logs
```powershell
# Check running containers and health status
docker compose ps

# View application logs
docker compose logs -f web

# View database logs
docker compose logs -f db
```

### Step 5: Stop and restart the containers
```powershell
# Stop containers while preserving database volume
docker compose stop

# Restart containers
docker compose start

# Completely shut down containers and networks
docker compose down
```

---

## 8. Kubernetes & Minikube Deployment (Windows 11)

All Kubernetes deployment manifests reside in the `k8s/` directory.

### Step 1: Start Minikube with Docker driver
Open PowerShell as Administrator:
```powershell
minikube start --driver=docker
```

### Step 2: Point local Docker CLI to Minikube's Docker daemon
This allows Minikube to use locally built Docker images without pushing to Docker Hub:
```powershell
& minikube -p minikube docker-env --shell powershell | Invoke-Expression
```

### Step 3: Build application image inside Minikube
```powershell
docker build -t library-app:latest .
```

### Step 4: Apply Kubernetes manifests in order
```powershell
# 1. ConfigMap and Secrets
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 2. PostgreSQL Persistent Volume Claim, Deployment, and Service
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml

# 3. Application Deployment and Service
kubectl apply -f k8s/app-deployment.yaml
```

### Step 5: Verify Pods, Services, and Probes
```powershell
kubectl get pods
kubectl get services
kubectl get pvc
```
Wait until both `library-postgres-deployment` and `library-app-deployment` pods show status `Running` (Ready 1/1).

### Step 6: Initialize database schema in Kubernetes
Run a one-off database initialization inside the web pod:
```powershell
$WEB_POD = (kubectl get pods -l app=library-management,tier=frontend -o jsonpath="{.items[0].metadata.name}")
kubectl exec -it $WEB_POD -- python scripts/init_db.py
kubectl exec -it $WEB_POD -- python scripts/seed_data.py
```

### Step 7: Access the application
Option A (Recommended for Minikube):
```powershell
minikube service library-app-service
```
This automatically opens the assigned Minikube URL in your default browser.

Option B (Port Forwarding):
```powershell
kubectl port-forward svc/library-app-service 5000:5000
```
Open `http://localhost:5000` in your browser.

### Step 8: View logs and restart application
```powershell
# View application pod logs
kubectl logs -f deployment/library-app-deployment

# Restart application deployment
kubectl rollout restart deployment library-app-deployment
```

### Step 9: Clean up Kubernetes resources safely
```powershell
kubectl delete -f k8s/app-deployment.yaml
kubectl delete -f k8s/postgres-deployment.yaml
kubectl delete -f k8s/postgres-pvc.yaml
kubectl delete -f k8s/secret.yaml
kubectl delete -f k8s/configmap.yaml
```

---

## 9. GitHub Setup & Push Commands

To upload this project to your GitHub account:

### Step 1: Stage and commit all files
```powershell
git add .
git commit -m "Initial commit: Library Management System complete project"
```

### Step 2: Create a repository on GitHub
Create a new empty repository named `library-management-system` on GitHub (do NOT check initialize with README/license as we already have them).

### Step 3: Link remote and push
```powershell
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/library-management-system.git
git branch -M main
git push -u origin main
```

---

## 10. Render Cloud Deployment

Render deployment runs your Flask app on a managed cloud container and connects it to a managed Render PostgreSQL database.

### Method 1: Automated Blueprint Deployment via `render.yaml`
1. Go to [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** > **Blueprint**.
3. Connect your GitHub repository `library-management-system`.
4. Render detects `render.yaml` and provisions:
   - Web Service (`library-management-system`)
   - Managed PostgreSQL Database (`library-postgres-db`)
5. Click **Apply**.

### Method 2: Manual Dashboard Setup
1. **Create Database:**
   - Click **New +** > **PostgreSQL**.
   - Name: `library-postgres-db`
   - Database: `library_db`
   - User: `library_user`
   - Plan: Free.
   - Click **Create Database**. Copy the **Internal Database URL**.
2. **Create Web Service:**
   - Click **New +** > **Web Service**.
   - Connect repository `library-management-system`.
   - Runtime: `Python 3`.
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 app:app`
   - Health Check Path: `/health`
   - In **Environment Variables**, add:
     - `PYTHON_VERSION`: `3.12.9`
     - `FLASK_ENV`: `production`
     - `SESSION_COOKIE_SECURE`: `true`
     - `SECRET_KEY`: *(Generate a secure random string)*
     - `DATABASE_URL`: *(Paste the Internal Database URL from Step 1)*
3. **Initialize Database Schema on Render:**
   - Once the web service is deployed, open the **Shell** tab in the Render Dashboard and run:
     ```bash
     python scripts/init_db.py
     python scripts/seed_data.py
     ```

---

## 11. Environment Variables Reference

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `FLASK_ENV` | Environment mode (`development`, `testing`, `production`) | `development` |
| `SECRET_KEY` | Secret key used for session cookie signing & CSRF | `dev-secret-key-...` |
| `DATABASE_URL` | SQLAlchemy database connection URI | `sqlite:///instance/library.db` or `postgresql://user:pass@host:5432/dbname` |
| `PORT` | HTTP port for server binding | `5000` |
| `DEFAULT_LOAN_DAYS` | Standard loan period in days | `14` |
| `SESSION_COOKIE_SECURE` | Enforce HTTPS secure cookie flag in production | `false` (local) / `true` (Render) |

---

## 12. Automated Test Suite

The test suite contains 23 automated unit and integration tests covering:
- Secure password hashing & verification.
- Student registration and uniqueness constraint enforcement.
- Role-based authorization and session state isolation.
- Book catalog creation, search, editing, and deletion.
- Inventory consistency: copies cannot be negative and available copies cannot exceed total copies.
- Book loan issue workflow and copy decrement.
- Rejecting issue requests for out-of-stock titles.
- Book return and copy increment back to inventory.
- Prevention of duplicate return submissions.
- Accurate overdue book detection.
- Application health check (`/health`) endpoint.

### Run Tests:
```powershell
python -m unittest discover tests -v
```

---

## 13. Screenshots Checklist for Project Evaluation

Capture the following screens to include in your project documentation and viva presentation slides:

1. [ ] **Public Landing Page:** Hero section, catalog stats, and features snapshot (`http://localhost:5000/`).
2. [ ] **Health Endpoint API:** JSON output showing healthy database status (`/health`).
3. [ ] **Librarian Login Page:** Clean sign-in form with demo account notes (`/auth/login`).
4. [ ] **Admin Dashboard:** Stat cards (Total copies, Available, Issued, Overdue alerts) and circulation table.
5. [ ] **Book Inventory Management:** Table of books, category filter, and search in action.
6. [ ] **Add/Edit Book Form:** Field validation and copy limits.
7. [ ] **Issue Book Page:** Selecting book, student, and due date with inventory warning.
8. [ ] **Active Issued Books Table:** Showing due countdown badges and overdue badges.
9. [ ] **Student Dashboard:** Student profile information and currently borrowed books.
10. [ ] **Student Catalog View:** Availability badges (`Available` vs `Checked Out`).
11. [ ] **Docker Containers Running:** Terminal screenshot showing `docker compose ps` and `docker compose logs`.
12. [ ] **Kubernetes / Minikube:** Terminal output showing `kubectl get pods,svc,pvc`.
13. [ ] **Render Cloud Deployment:** Render dashboard showing healthy service and live web URL.

---

## 14. Troubleshooting Common Errors

### 1. `psycopg2` / `pg_isready` Connection Errors
- **Cause:** PostgreSQL container or service is still initializing when the web app starts.
- **Solution:** In Docker Compose, the `condition: service_healthy` ensures the web container waits for `pg_isready` before starting. In Minikube, check `kubectl describe pod <postgres-pod>` to verify PVC binding.

### 2. Render Database URL Format (`postgres://` vs `postgresql://`)
- **Cause:** Render provides PostgreSQL connection strings starting with `postgres://`, but SQLAlchemy 1.4+ requires `postgresql://`.
- **Solution:** Our `config.py` contains automatic URL normalization (`get_database_url()`) that converts `postgres://` to `postgresql://` seamlessly.

### 3. Minikube Permission Denied on Windows
- **Cause:** PowerShell lacks permissions to create `.minikube` in user directory or virtualization is disabled in BIOS.
- **Solution:** Run PowerShell as Administrator and ensure Hyper-V or WSL 2 is enabled in Windows features.

---

## 15. License & Academic Attribution
Developed as an open-source educational microproject for computer science students demonstrating Full-Stack Web Development, Docker Containerization, Kubernetes Orchestration, and Cloud Hosting. Free to adapt and submit for academic project evaluations.
