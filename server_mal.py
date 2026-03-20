# main.py

ADMIN_CODE = "z%P7&e!t2*B@dQ9"


import os
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, send, emit
from datetime import datetime
from collections import deque

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", path="/chat/socket.io")


# Serve the HTML page
@app.route("/chat")
def index():
    return send_from_directory(os.path.dirname(__file__), "main.html")




# -----------------------------
# Chat logic
# -----------------------------
clients = set()
active_usernames = {}  # sid -> current username
admins = {}
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
last_day = datetime.now().date()


# Helper to update daily reset
history = deque(maxlen=100)
#     global last_day, history, timestamp
#     today = datetime.now().date()
#     if today != last_day:
#         timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
history.append(f"[{timestamp}] [!] Server         > Room reset after inactivity")
#         last_day = today


# When a client connects
@socketio.on("connect")
def handle_connect():
    # daily_reset()
    sid = request.sid
    clients.add(sid)
    active_usernames[sid] = "Anonymous"
    admins[sid] = False

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    join_msg = f"[{timestamp}] [!] Server         > Someone entered the room"

    if len(clients) == 1:
        c_num_alert = (
            f"[{timestamp}] [!] Server         > There is 1 person in the room"
        )
    else:
        c_num_alert = f"[{timestamp}] [!] Server         > There are {len(clients)} people in the room"

    # Send join messages to everyone except the new client
    for client_sid in clients:
        emit("message", join_msg, room=client_sid)
        emit("message", c_num_alert, room=client_sid)

    # Send full history to the new client
    for msg in history:
        emit("message", msg, room=sid)

    # Send welcome to the new client

    # Add to history
    history.append(join_msg)
    history.append(c_num_alert)





# When a client requests a name change
@socketio.on("name_change_request")
def handle_name_change_request(new_name):
    sid = request.sid
    current_name = active_usernames.get(sid, "Anonymous")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    force_fail = False

    if admins[sid]:
        if new_name.lower() == "unadmin":
            msg = (
                f"[{ts}] [!] Server         > User {current_name} gave up administrative powers"
            )
            send(
                msg,
                broadcast=True,
                include_self=True,
            )
            history.append(msg)
            admins[sid] = False
            return
        else:
            force_fail = True

    if new_name == ADMIN_CODE:
        return

    if not new_name:
        new_name = "Anonymous"
    taken = any(v == new_name for k, v in active_usernames.items() if k != sid)
    if taken or new_name == current_name or force_fail:
        msg = f"[{ts}] [!] Server         > User {current_name} failed to change their name"
        send(
            msg,
            broadcast=True,
            include_self=True,
        )
        history.append(msg)
        return

    active_usernames[sid] = new_name
    change_msg = f"[{ts}] [!] Server         > User {current_name} changed their name to {new_name}"
    history.append(change_msg)
    send(change_msg, broadcast=True, include_self=True)
    emit("name_change_approved", new_name)


# When a client requests admin powers
@socketio.on("admin_request")
def handle_admin_request(code):
    sid = request.sid
    current_name = active_usernames.get(sid, "Anonymous")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if code != ADMIN_CODE or admins[sid] == True:
        return

    new_name = "Admin"
    tag = 2
    taken = any(v == new_name for k, v in active_usernames.items() if k != sid)
    while taken:
        tag += 1

        taken = any(v == new_name for k, v in active_usernames.items() if k != sid)
        new_name = "Admin (" + str(tag) + ")"

    active_usernames[sid] = new_name
    admin_msg = (
        f"[{ts}] [!] Server         > User {current_name} gained administrative powers"
    )

    history.append(admin_msg)
    send(admin_msg, broadcast=True, include_self=True)
    emit("admin_approved", new_name)
    admins[sid] = True


# When a client sends a chat message
@socketio.on("chat_message")
def handle_message(msg):
    sid = request.sid
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if admins[sid] == True:
        full_msg = f"[{ts}] [!] {msg}"
    else:
        full_msg = f"[{ts}] [?] {msg}"
    history.append(full_msg)

    # Broadcast to everyone including sender
    send(full_msg, broadcast=True)


# When a client disconnects
@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    if sid in clients:
        clients.remove(sid)
    active_usernames.pop(sid, None)
    admins.pop(sid, None)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    leave_msg = f"[{ts}] [!] Server         > Someone left the room"
    history.append(leave_msg)

    if len(clients) == 1:
        c_num_alert = f"[{ts}] [!] Server         > There is 1 person in the room"
    elif len(clients) == 0:
        c_num_alert = f"[{ts}] [!] Server         > The room is empty"
    else:
        c_num_alert = (
            f"[{ts}] [!] Server         > There are {len(clients)} people in the room"
        )

    # Broadcast leave messages
    send(leave_msg, broadcast=True)
    send(c_num_alert, broadcast=True)
    history.append(c_num_alert)


# -----------------------------
# Run Flask + SocketIO
# -----------------------------
if __name__ == "__main__":
   socketio.run(app, host="127.0.0.1", port=5333, allow_unsafe_werkzeug=True)
