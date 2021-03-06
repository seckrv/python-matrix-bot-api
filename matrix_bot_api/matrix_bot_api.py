import traceback
import re
from matrix_client.client import MatrixClient
from matrix_client.api import MatrixRequestError


class MatrixBotAPI:

    # username - Matrix username
    # password - Matrix password
    # server   - Matrix server url : port
    # rooms    - List of rooms ids to operate in, or None to accept all rooms
    def __init__(self, username, password, server, rooms=None):
        self.username = username

        # Authenticate with given credentials
        self.client = MatrixClient(server)
        try:
            self.client.login_with_password(username, password)
        except MatrixRequestError as e:
            print(e)
            if e.code == 403:
                print("Bad username/password")
        except Exception as e:
            print("Invalid server URL")
            traceback.print_exc()

        # Store allowed rooms
        self.rooms = rooms

        # Store empty list of handlers
        self.handlers = []

        # Store dict with additional arguments to handlers
        # This allows to provide additional arguments to a specific handler
        # callback on registration.
        self.additional_arguments = {}

        # If rooms is None, we should listen for invites and automatically accept them
        if rooms is None:
            self.client.add_invite_listener(self.handle_invite)
            self.rooms = []

            # Add all rooms we're currently in to self.rooms and add their callbacks
            for room_id, room in self.client.get_rooms().items():
                room.add_listener(self.handle_message)
                self.rooms.append(room_id)
        else:
            # Add the message callback for all specified rooms
            for room in self.rooms:
                room.add_listener(self.handle_message)

    # Add a new handler to the bot. If arg is given, it is provided as a third
    # argument on every invocation of handler.
    def add_handler(self, handler, arg=None):
        self.handlers.append(handler)

        if arg:
            self.additional_arguments[handler] = arg

    def remove_handler(self, handler):
        try:
            self.handlers.remove(handler)
        except ValueError as e:
            return

        try:
            self.additional_arguments.pop(handler)
        except KeyError:
            return

    def get_handler(self, trigger):
        res = []

        for h in self.handlers:
            if h.triggers_on(trigger):
                res.append(h)

        return res


    def handle_message(self, room, event):
        # Make sure we didn't send this message
        if re.match("@" + self.username, event['sender']):
            return

        # Loop through all installed handlers and see if they need to be called
        for handler in self.handlers:
            if handler.test_callback(room, event):
                # This handler needs to be called
                try:
                    # If an additional argument is registered for the handler,
                    # call it with this argument
                    arg = self.additional_arguments[handler]
                    handler.handle_callback(room, event, arg)
                except KeyError:
                    # Otherwise leave it out
                    handler.handle_callback(room, event)


    def handle_invite(self, room_id, state):
        print("Got invite to room: " + str(room_id))
        print("Joining...")
        room = self.client.join_room(room_id)

        # Add message callback for this room
        room.add_listener(self.handle_message)

        # Add room to list
        self.rooms.append(room)

    def start_polling(self):
        # Starts polling for messages
        self.client.start_listener_thread()
        return self.client.sync_thread
