"""Development entry point: ``python run.py`` (use a WSGI server in production)."""
from eventhub.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
