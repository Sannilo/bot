# Project Overview
This project is a **Telegram Web App** that integrates a web interface, built with Flask, directly into the Telegram environment. Its operation is supported by a Telegram bot component that handles commands and user interactions.

# Rules for `examples\` folder

* **Everything in this folder is for example purposes only.** Do not connect these files to the working application, as I will delete the `examples\` folder in the future.
* **Strictly do not change the files in the `handlers\` folder,** as these are the bot's files.
* **Make edits** only in the `webappnew\` folder.
* **Always:** respond in Russian language.

The project consists of two main components working together:

* **Web Application (WebApp):** The web application is built on the Flask framework. It provides the main web interface for users, which opens directly inside Telegram for managing accounts, profiles, and making payments. The web application code is located in the `webappnew/web/` directory, with templates in `webappnew/templates/` and static files in `webappnew/static/`.
* **Telegram Bot:** The bot is built on the `pyTelegramBotAPI` library and serves as the connecting link. It processes user commands, launches the Web App, and sends notifications. The main bot logic is in `webappnew/botapp.py` and `webappnew/core.py`.
* **Database:** The project uses a SQLite database (`instance/database.db`) with SQLAlchemy as the ORM. The database schema includes tables for users, keys, and other application data, as described in `bd.md`.
* **Payments:** The application is integrated with Stripe for payment processing, which is managed through `webappnew/payment_processor.py`.

# Building and Running

1.  **Install Dependencies:**
    The project's Python dependencies are listed in `webappnew/requirements.txt`. To install them, run:
    ```bash
    pip install -r webappnew/requirements.txt
    ```

2.  **Running the Application:**
    The main entry point for the application is `webappnew/botapp.py`. To run the bot and the web server, execute:
    ```bash
    python webappnew/botapp.py
    ```
    This will start the Flask development server and begin polling for Telegram updates.

# Development Conventions

* **Frameworks:** The project uses Flask for the web backend and `pyTelegramBotAPI` for the Telegram bot.
* **Database:** SQLAlchemy is used for database interactions. The database models are defined within the application code.
* **Structure:** The code is separated into a `webappnew` package, with sub-packages for web handlers, bot logic, and core functionality.
* **Configuration:** Application configuration, such as API keys and database URIs, is likely managed within the Python files. Sensitive information should be handled securely and not hardcoded directly in the source code.