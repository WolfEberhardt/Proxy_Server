import socket
import select
import threading
import os
import logging


class Proxy:
    PORT = 8888
    mode = False
    IP = "localhost"
    def __init__(self) -> None:
        self.running = True
        self.toast = ToastNotifier()
        with open(os.path.dirname(__file__) + "/files/proxy.log", "w", encoding="utf-8") as logging_file:
            logging_file.write("")
        logging.basicConfig(format="%(levelname)s:%(name)s:%(message)s", filename=os.path.dirname(__file__) + "/files/proxy.log", level=logging.DEBUG, encoding="utf-8")

    def run(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((Proxy.IP, Proxy.PORT))
            self.server.listen(5)
            logging.debug(f"Proxy-Server läuft auf {Proxy.IP}:{Proxy.PORT}")
            print(f"Proxy-Server läuft auf {Proxy.IP}:{Proxy.PORT}")
            self.start_thread()
        except Exception as e:
            logging.error(f"Fehler beim Starten des Servers: {e}")

    def is_address_blocked(self, address):
        try:
            with open(os.path.dirname(__file__) + "/files/blocked.txt", "r", encoding="utf-8") as ba:
                BLOCKED_ADDRESSES = ba.read().splitlines()
                return address in BLOCKED_ADDRESSES
        except Exception as e:
            logging.error(f"Fehler beim Lesen der Blockliste: {e}")
            return False
    
    def get_host_header(self, request):
        headers = request.decode(errors='ignore').split('\r\n')
        for header in headers:
            if header.lower().startswith('host:'):
                return header.split(':')[1].strip()
        return None

    def extract_host_from_url(self, url):
        if url.startswith('http://'):
            url = url[7:]
        elif url.startswith('https://'):
            url = url[8:]
        
        print(url)
        return url.split('/')[0]

    def handle_client(self, client_socket):
        try:
            request = client_socket.recv(4096)
            if not request:
                logging.debug("Keine Antwort")
                return

            request_text = request.decode(errors='ignore')
            first_line = request_text.split('\n')[0]
            method = first_line.split()[0]

            url = first_line.split()[1]
            target_address = self.get_host_header(request)
            xx = target_address
            if not target_address:
                target_address = self.extract_host_from_url(url)

            target_address = target_address.split(':')[0]

            if self.is_address_blocked(target_address):
                client_socket.close()
                return
            print(target_address)

            if method == 'GET':
                target_port = 80
                target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                target_socket.connect((target_address, target_port))
                target_socket.sendall(request)

                while self.running:
                    response = target_socket.recv(16384)
                    if not response:
                        break
                    client_socket.sendall(response)

                target_socket.close()

            elif method == 'CONNECT':
                client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")

                target_port = 443
                target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                target_socket.connect((target_address, target_port))

                while self.running:
                    rlist, _, _ = select.select([client_socket, target_socket], [], [])
                    if client_socket in rlist:
                        data = client_socket.recv(4096)
                        if not data:
                            break
                        target_socket.sendall(data)
                    if target_socket in rlist:
                        data = target_socket.recv(4096)
                        if not data:
                            break
                        client_socket.sendall(data)

                target_socket.close()

        except Exception as e:
            logging.error(f"Ein Fehler ist aufgetreten: {e}")
        finally:
            client_socket.close()


    def start_thread(self):
        while self.running:
            try:
                client_sock, addr = self.server.accept()
                threading.Thread(target=self.handle_client, daemon=True, args=(client_sock,)).start()
            except KeyboardInterrupt:
                os._exit(0)


if __name__ == "__main__":
    pr = Proxy()
    pr.run()
