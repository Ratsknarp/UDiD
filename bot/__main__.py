import os 
from bot import app, handlers


if __name__ == "__main__":
    os.makedirs("temp", exist_ok=True)
    app.run_polling(drop_pending_updates=True)
