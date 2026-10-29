import uvicorn


def main():
    """Runs the FastAPI server listening on all network interfaces (0.0.0.0:8000)."""
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()

