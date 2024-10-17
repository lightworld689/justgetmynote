# JustGetMyNote Server

[简体中文](https://github.com/lightworld689/justgetmynote/blob/main/README_zhcn.md)

**JustGetMyNote** is a simple note-taking server based on the Flask framework. It allows users to manage and display text content. The server supports content retrieval from an SQLite database or from the `main.txt` file, and provides a front-end interface for users to view and edit content.

All requests are logged to a log file for tracking and management. Additionally, the server supports generating shareable links and a maintenance mode to restrict content modification and access when needed. The CSS and some functionalities are inspired by [note.ms](https://note.ms).

**Now you can share your notes with others, including burn-after-read links!**

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [Accessing Content](#accessing-content)
  - [Read-Only Content](#read-only-content)
  - [Editable Content](#editable-content)
  - [Shareable Links](#shareable-links)
  - [Burn After Read Links](#burn-after-read-links)
- [Editing and Updating](#editing-and-updating)
- [Logging](#logging)
- [Static Files](#static-files)
  - [Background Image](#background-image)
  - [Website Icons](#website-icons)
- [Maintenance Mode](#maintenance-mode)
- [Customization and Extension](#customization-and-extension)
- [Notes](#notes)
- [License](#license)

## Features

- **Content Management**:
  - Retrieve content based on different URL paths from an SQLite database or `main.txt` file.
  - Support viewing and editing content.
  - If the content identifier does not exist, automatically create a new database record.
  - Generate shareable links (`/share/<share_id>`) to display content in read-only mode.
  - **New**: Generate burn-after-read links (`/burn/<burn_id>`) that allow content to be viewed only once before being deleted.

- **Front-end Interaction**:
  - CSS inspired by [note.ms](https://note.ms).
  - Auto-save functionality that detects content changes every second and updates the server.
  - "Share" button to generate shareable links for read-only content.
  - **New**: "Share (Burn after read)" button to generate burn-after-read links.
  - Different information displayed in read-only and editable modes.
  - Display notifications for successful saves.

- **Logging**:
  - Log each request's IP, request path, and method to `log.log` in the format: `IP - Request Path - POST/GET`.

- **Initialization**:
  - Automatically initialize the SQLite database, `main.txt` file, background image `meta/bg.png`, icons `favicon.ico` and `meta/app.png` if they do not exist.
  - Support maintenance mode enabled via the `settings/main.txt` configuration file.

- **Caching Mechanism**:
  - Regularly (every 10 seconds) read `main.txt` and `settings/main.txt` from the file system to update the in-memory cache for improved access efficiency.
  - Use a write queue to handle database writes asynchronously.

- **Burn After Read Functionality**:
  - Users can create burn-after-read links that can be accessed only once.
  - After accessing the burn-after-read link, the content is deleted from the database and cache.

## Project Structure

```
JustGetMyNote/
│
├── server.py                # Server code
├── main.txt                 # Main text file (auto-created)
├── content.db               # SQLite database file (auto-created)
├── log.log                  # Log file (auto-created)
├── favicon.ico              # Website icon (auto-created)
├── meta/
│   ├── bg.png               # Background image (auto-created)
│   ├── app.png              # Application icon (auto-created)
│   └── favicon.png          # Favicon image (auto-created)
├── lib/
│   ├── abc.css              # CSS styles (auto-created)
│   └── abc.js               # JavaScript (auto-created)
├── settings/
│   └── main.txt             # Settings file (for maintenance mode)
├── requirements.txt         # Python dependencies
├── README.md                # This README file (English)
└── readme_zhcn.md           # Chinese README file
```

## Prerequisites

- **Python 3.6+**: Ensure Python is installed.
- **Dependencies**:
  - `Flask`: For building the server.
  - `Pillow`: For creating placeholder images and icons.
  - `asgiref`: For ASGI support.
- **Optional**:
  - `Gunicorn` or any ASGI server to run the application in production.

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/yourusername/JustGetMyNote.git
   cd JustGetMyNote
   ```

2. **Create and activate a virtual environment (optional but recommended)**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

   **`requirements.txt` content example**:

   ```plaintext
   Flask
   Pillow
   asgiref
   ```

## Running the Server

In the project's root directory, run the following command to start the server:

```bash
python server.py
```

The server will listen on `0.0.0.0:6094`. On the first run, the script will automatically initialize the database and necessary files if they do not exist.

**Sample Output**:

```
Database initialized.
main.txt created.
meta folder created.
meta/bg.png created. Please replace it with your desired background image.
meta/app.png created. Please replace it with your desired app icon.
favicon.ico created. Please replace it with your desired favicon.ico.
settings folder created.
settings/main.txt created.
 * Serving Flask app 'server'
 * Running on http://0.0.0.0:6094/ (Press CTRL+C to quit)
```

**Note**: For production environments, it is recommended to use an ASGI server like Uvicorn or Hypercorn.

### Running with Uvicorn (ASGI Server)

Install Uvicorn:

```bash
pip install uvicorn
```

Run the server:

```bash
uvicorn server:main --host 0.0.0.0 --port 6094
```

## Accessing Content

### Read-Only Content

Accessing the following paths will display the content of `main.txt` in read-only mode:

- [http://localhost:6094/](http://localhost:6094/)
- [http://localhost:6094/0](http://localhost:6094/0)
- [http://localhost:6094/1](http://localhost:6094/1)
- [http://localhost:6094/main](http://localhost:6094/main)
- [http://localhost:6094/index](http://localhost:6094/index)

At the bottom, it will display:

```
JustGetMyNote - /path - ReadOnly
```

### Editable Content

Accessing paths with identifiers matching the regex `[A-Za-z0-9]{1,24}` (1-24 letters or numbers) will retrieve corresponding content from the SQLite database and display it in editable mode:

- [http://localhost:6094/abcd](http://localhost:6094/abcd)
- [http://localhost:6094/efgh](http://localhost:6094/efgh)

At the bottom, it will display:

```
JustGetMyNote - /abcd
```

If the identifier does not exist, the page will be blank, allowing you to create new content through the edit box.

### Shareable Links

After generating a shareable link, you can access it to view the content in read-only mode:

- [http://localhost:6094/share/<share_id>](http://localhost:6094/share/<share_id>)

Shareable link example:

```
JustGetMyNote - Shared with you - ReadOnly
```

### Burn After Read Links

You can create a burn-after-read link that can be accessed only once. After viewing, the content is deleted.

- [http://localhost:6094/burn/<burn_id>](http://localhost:6094/burn/<burn_id>)

Burn-after-read link example:

```
JustGetMyNote - /burn/<burn_id> - Burn after read
```

After accessing this link, the content will be permanently deleted.

## Editing and Updating

In the editable page, after modifying the content, the client-side JavaScript detects content changes every second:

- If content changes are detected, it automatically sends a `POST` request to the `/update/<id>` path.
- The server receives the request and updates or inserts the corresponding content into the SQLite database.
- Upon successful update, the console will display "Update successful", and `lastContent` is updated to avoid duplicate submissions.

**Update Request Example**:

```json
{
  "status": "success"
}
```

If the update fails, an appropriate error message will be returned.

## Logging

All access logs are recorded in the `log.log` file in the following format:

```
127.0.0.1 - /abcd - GET
127.0.0.1 - /abcd - POST
```

Each log entry includes:

- **IP Address**: The client's IP that initiated the request.
- **Request Path**: The accessed URL path.
- **Request Method**: `GET` or `POST`.

## Static Files

### Background Image

The default background image is stored in `meta/bg.png`. On the first run, the script creates a transparent PNG placeholder. Please replace it with your desired background image.

Access [http://localhost:6094/meta/bg.png](http://localhost:6094/meta/bg.png) to view the background image.

### Website Icons

`favicon.ico` is stored in the project's root directory. On the first run, the script creates a transparent PNG placeholder. Please replace it with your desired icon.

Access [http://localhost:6094/favicon.ico](http://localhost:6094/favicon.ico) to view the website icon.

Application icon `meta/app.png` is used for devices that support touch icons.

## Maintenance Mode

You can enable or disable maintenance mode (Construction Mode) by editing the `settings/main.txt` file.

**Enable Maintenance Mode**:

Set `construction = true` in `settings/main.txt`:

```ini
# Change this to enter read-only mode and the user will not be able to modify anything.
construction = true
```

When enabled, all editable pages will be displayed in read-only mode, and users cannot create share links or modify content.

**Disable Maintenance Mode**:

Set `construction` to `false`:

```ini
# Change this to enter read-only mode and the user will not be able to modify anything.
construction = false
```

After changing, the server will apply the new settings during the next cache update.

## Customization and Extension

- **Adding New Content**:
  - By accessing a new identifier path (e.g., `/ijkl`), and entering content in the editable page, the server will automatically create a new database record.

- **Generating Share Links**:
  - Click the "Share" button in the editable page to generate a shareable link that displays the content in read-only mode.

- **Generating Burn After Read Links**:
  - Click the "Share (Burn after read)" button to generate a burn-after-read link.

- **Changing Port**:
  - Modify the `PORT` variable in `server.py` to change the server's listening port.

- **Replacing Background Image and Icons**:
  - Replace `meta/bg.png`, `meta/app.png`, and `favicon.ico` in the project root directory with your desired images and icons.

- **Extending Content Fields**:
  - You can add more fields to the `contents` table, such as titles, timestamps, etc., to extend functionality.

## Notes

- **Security**:
  - The current example does not implement authentication or access control. In a production environment, ensure to add necessary security measures like authentication and permission management to prevent unauthorized access and modification.

- **Error Handling**:
  - Error handling is basic. Enhance error handling and user feedback as needed to ensure users receive clear prompts in various exceptional circumstances.

- **Dependencies**:

  Ensure all dependencies are installed:

  ```bash
  pip install -r requirements.txt
  ```

- **Concurrent Access**:
  - The server uses multi-threading (`threaded=True`) to support concurrent access. For high-load applications, consider using a more robust WSGI or ASGI server like Gunicorn or Uvicorn.

- **Data Backup**:
  - Regularly back up `content.db` and related files to prevent data loss.

## License

This project is licensed under the [AGPL 3.0 License](LICENSE).

---

**Thank you for using JustGetMyNote!**

If you have any questions or suggestions, feel free to submit an [issue](https://github.com/lightworld689/JustGetMyNote/issues) or contact the author.
