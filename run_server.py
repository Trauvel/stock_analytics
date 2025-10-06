"""Запуск FastAPI сервера."""

import uvicorn
from app.api.server import app

if __name__ == "__main__":
    print("=" * 80)
    print("Starting Stock Analytics API Server")
    print("=" * 80)
    print("\nAPI Documentation will be available at:")
    print("  - Swagger UI: http://localhost:8000/docs")
    print("  - ReDoc:      http://localhost:8000/redoc")
    print("\nEndpoints:")
    print("  - GET  /health          - Check server health")
    print("  - GET  /tickers         - List all tracked tickers")
    print("  - GET  /report/today    - Get latest analysis report")
    print("  - GET  /report/summary  - Get report summary")
    print("  - POST /portfolio       - Save portfolio")
    print("  - GET  /portfolio/view  - View saved portfolio")
    print("\n" + "=" * 80)
    print("Press Ctrl+C to stop the server")
    print("=" * 80 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )

