from aiohttp import web
import ssl
import subprocess
import argparse
import os
import logging

logging.basicConfig(level=logging.DEBUG, format=" - %(message)s")
ERRONOUS_PASSWORD_TRIES = 0


async def check_authenticated(request):
    global ERRONOUS_PASSWORD_TRIES
    token = request.headers.get("Authorization")
    if not request.app.get("auth_password", None):
        return True
    if token == request.app.get("auth_password"):
        return True
    ERRONOUS_PASSWORD_TRIES += 1
    if request.app.get(
        "sensitive"
    ) != -1 and ERRONOUS_PASSWORD_TRIES >= request.app.get("sensitive"):
        os._exit(-1)
    return False


async def login_required_middleware(request, handler):
    authenticated = await check_authenticated(request)
    if not authenticated:
        return web.Response(text="Unauthorized", status=401)
    return await handler(request)


def login_required(handler):
    async def wrapped_handler(request):
        return await login_required_middleware(request, handler)

    return wrapped_handler


@login_required
async def handle(request):
    script_name = request.match_info.get("script_name")
    if script_name:
        scripts_folder = os.path.join(
            os.getcwd(), request.app.get("scripts_folder", "")
        )
        script_path = os.path.join(scripts_folder, script_name)
        if os.path.exists(script_path):
            try:
                result = subprocess.run(
                    ["bash", script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                return web.json_response(
                    {
                        "status": "success",
                        "output": result.stdout.decode("utf-8"),
                        "error": result.stderr.decode("utf-8"),
                    }
                )
            except Exception as e:
                return web.json_response(
                    {"status": "error", "error_message": str(e)}
                )
        else:
            return web.json_response(
                {"status": "error", "error_message": "Script not found"}
            )
    else:
        return web.json_response(
            {"status": "error", "error_message": "No script name provided"}
        )


async def handle_list_commands(request):
    commands = []
    for filename in os.listdir(request.app.get("scripts_folder")):
        if filename.endswith(".sh") or filename.endswith(".py"):
            commands.append(filename)
    return web.json_response({"commands": commands})


def create_ssl_context(certfile, keyfile):
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    try:
        ssl_context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        return ssl_context
    except:
        return None


def run():
    parser = argparse.ArgumentParser(
        description="Run a server for executing custom scripts over HTTPS."
    )
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host IP address to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8443")),
        help="Port number for the server (default: 8443)",
    )
    parser.add_argument(
        "--certfile",
        default=os.getenv("CERT_FILE", "path/to/your/certfile.pem"),
        help="Path to SSL certificate file",
    )
    parser.add_argument(
        "--keyfile",
        default=os.getenv("KEY_FILE", "path/to/your/keyfile.pem"),
        help="Path to SSL private key file",
    )
    parser.add_argument(
        "--scripts-folder",
        default=os.getenv("SCRIPTS_FOLDER", os.getcwd()),
        help="Path to the folder containing available scripts",
    )
    parser.add_argument(
        "--auth-password",
        default=os.getenv("AUTH_PASSWORD", None),
        help="Password for authentication (default: None)",
    )
    parser.add_argument(
        "--sensitive",
        default=1,
        help="Amount of wrong password the server can receive before killing it-self",
    )
    parser.add_argument(
        "--ntfy", default=None, help="ntfy.sh notification room"
    )

    args = parser.parse_args()
    HOST = args.host
    PORT = args.port
    CERT_FILE = args.certfile
    KEY_FILE = args.keyfile
    SCRIPTS_FOLDER = args.scripts_folder
    AUTH_PASSWORD = args.auth_password
    NOTIFY = args.ntfy
    SENSITIVE = args.sensitive

    if AUTH_PASSWORD is None:
        print(
            "Warning: No authentication password provided. Requests will not be authenticated."
        )
    app = web.Application()
    app["auth_password"] = AUTH_PASSWORD
    app["notify"] = NOTIFY
    app["scripts_folder"] = SCRIPTS_FOLDER
    app["sensitive"] = SENSITIVE
    app.router.add_post("/{script_name}", login_required(handle))
    app.router.add_get("/", login_required(handle_list_commands))

    ssl_context = create_ssl_context(CERT_FILE, KEY_FILE)

    web.run_app(app, host="0.0.0.0", port=PORT, ssl_context=ssl_context)


if __name__ == "__main__":
    run()
