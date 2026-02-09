# 📊 Moodle Learning Analytics Pipeline

A privacy-aware local data pipeline for transforming raw Moodle logs into structured, anonymised, and interpretable course-level analytics.

---

## 🧱 Development Setup (Docker)

### 1️⃣ Install Docker Desktop
Download and install Docker Desktop for Windows or Mac:  
https://www.docker.com/products/docker-desktop/

Make sure Docker Desktop is running before proceeding.

---

### 2️⃣ Clone the repository

```bash
git clone <REPO_URL>
cd moodle-analytics-pipeline
```
### 3️⃣ Create environment file
Copy the example file:

```bash
cp .env.example .env
```
If using Windows PowerShell:

```bash
copy .env.example .env
```

Default development values are sufficient.

### 4️⃣ Start the application
```bash
docker compose up --build
```

After startup, open: http://localhost:8501

You should see the Streamlit interface.

### 5️⃣ Stop the application

```bash
docker compose down
```
---
### Architecture

PostgreSQL (Docker container)

Streamlit app (Docker container)

Shared Docker network

Environment variables managed via .env

📁 Project Structure
```
app/                  # Streamlit UI
src/                  # ETL and processing logic
sql/                  # Database schema files
docker-compose.yml
Dockerfile
requirements.txt
.env.example

```

⚠ Notes

.env is not committed to Git (contains configuration values).
Do not commit real Moodle log data.

data/ folder should remain ignored by Git.
