# Fleety Backend - FastAPI + MongoDB

## Setup Instructions

### 1. Prerequisites
- Python 3.8+
- MongoDB (local or Atlas)
- pip

### 2. Installation

#### Create virtual environment (optional but recommended)
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

#### Install dependencies
```bash
pip install -r requirements.txt
```

### 3. MongoDB Setup

#### Option A: Local MongoDB
1. Install MongoDB Community Edition from https://www.mongodb.com/try/download/community
2. Start MongoDB service:
   - Windows: `mongod`
   - macOS: `brew services start mongodb-community`
   - Linux: `sudo systemctl start mongod`

#### Option B: MongoDB Atlas (Cloud)
1. Go to https://www.mongodb.com/cloud/atlas
2. Create a free cluster
3. Update `.env` with your connection string:
   ```
   MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net
   ```

### 4. Configuration
1. Copy `.env.example` to `.env` (already done)
2. Update `.env` with your settings:
   - `MONGODB_URL`: Your MongoDB connection string
   - `SECRET_KEY`: Change to a strong secret key for production
   - `CORS_ORIGINS`: Add your frontend URL if different

### 5. Run the Application

```bash
python -m uvicorn app.main:app --reload
```

Or use the provided startup script:
```bash
python app/main.py
```

Server will be available at: `http://localhost:8000`
API Docs at: `http://localhost:8000/docs`

### 6. API Endpoints

#### Authentication
- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user

#### Vehicles
- `GET /api/vehicles` - List all vehicles
- `POST /api/vehicles` - Create new vehicle
- `GET /api/vehicles/{vehicle_id}` - Get vehicle details
- `PUT /api/vehicles/{vehicle_id}` - Update vehicle
- `DELETE /api/vehicles/{vehicle_id}` - Delete vehicle

#### Maintenance Records
- `GET /api/maintenance/vehicle/{vehicle_id}` - Get maintenance records
- `POST /api/maintenance/vehicle/{vehicle_id}` - Create maintenance record
- `GET /api/maintenance/{maintenance_id}` - Get record details
- `PUT /api/maintenance/{maintenance_id}` - Update record
- `DELETE /api/maintenance/{maintenance_id}` - Delete record

#### Reminders
- `GET /api/reminders/vehicle/{vehicle_id}` - Get reminders
- `POST /api/reminders/vehicle/{vehicle_id}` - Create reminder
- `GET /api/reminders/{reminder_id}` - Get reminder details
- `PUT /api/reminders/{reminder_id}` - Update reminder
- `DELETE /api/reminders/{reminder_id}` - Delete reminder

### 7. Example Requests

#### Signup
```bash
curl -X POST "http://localhost:8000/api/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123","full_name":"John Doe"}'
```

#### Login
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

#### Add Vehicle
```bash
curl -X POST "http://localhost:8000/api/vehicles" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"make":"Toyota","model":"Camry","year":2020,"color":"Silver","current_mileage":45000}'
```

### 8. Development Notes

- All requests (except signup/login) require `Authorization: Bearer <token>` header
- Tokens expire after 24 hours (configurable in .env)
- MongoDB data is automatically indexed for optimized queries
- CORS is configured to accept requests from frontend running on localhost:5173

### 9. Production Deployment

Before deploying:
1. Change `SECRET_KEY` to a secure random string
2. Set `DEBUG=False`
3. Update `CORS_ORIGINS` to your production frontend URL
4. Use a production MongoDB instance (Atlas recommended)
5. Consider using environment variables instead of .env file
6. Add additional security measures (rate limiting, input validation, etc.)

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration settings
│   ├── database.py          # MongoDB connection
│   ├── models/              # Database models
│   │   ├── user.py
│   │   ├── vehicle.py
│   │   ├── maintenance.py
│   │   ├── reminder.py
│   ├── schemas/             # Pydantic schemas for validation
│   │   ├── user.py
│   │   ├── vehicle.py
│   │   ├── maintenance.py
│   │   ├── reminder.py
│   ├── routes/              # API route handlers
│   │   ├── auth.py
│   │   ├── vehicles.py
│   │   ├── maintenance.py
│   │   ├── reminders.py
│   ├── utils/               # Utility functions
│   │   └── auth.py          # JWT and password utilities
├── requirements.txt         # Python dependencies
├── .env.example             # Example environment variables
├── .env                     # Local environment variables (git ignored)
└── README.md               # This file
```

## Technology Stack

- **Framework**: FastAPI (async Python web framework)
- **Database**: MongoDB (NoSQL document database)
- **Authentication**: JWT (JSON Web Tokens)
- **Password Hashing**: Bcrypt
- **Validation**: Pydantic
- **Server**: Uvicorn (ASGI server)
- **CORS**: Handled by FastAPI middleware

## Troubleshooting

### MongoDB Connection Error
- Ensure MongoDB is running: `mongod` or check service status
- Verify connection string in .env
- For MongoDB Atlas, allow your IP in the firewall

### Import Errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` again

### Token Errors
- Verify Authorization header format: `Authorization: Bearer <token>`
- Check if token has expired (24 hours default)
