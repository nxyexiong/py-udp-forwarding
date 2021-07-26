import socket
import select
import threading
import time
import sys

CONN_TIMEOUT = 60 * 60 * 12 # 12 hours


class Conn:
 def __init__(self, client_addr, target_addr, recv_cb):
  self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  self.sock.bind(('', 0))
  self.client_addr = client_addr
  self.target_addr = target_addr
  self.recv_cb = recv_cb
  self.last_active_time = time.time()
  self.run_thread = None
  self.running = False

 def run(self):
  self.running = True
  self.run_thread = threading.Thread(target=self.handle_recv)
  self.run_thread.start()

 def close(self):
  self.running = False
  if self.run_thread is not None:
   while self.run_thread.is_alive():
    time.sleep(1)
  self.sock.close()

 def send(self, data):
  self.sock.sendto(data, self.target_addr)
  self.last_active_time = time.time()

 def handle_recv(self):
  while self.running:
   readable, _, _ = select.select([self.sock, ], [], [], 1)
   if not readable:
    continue
   data, addr = self.sock.recvfrom(2048)
   self.recv_cb(data, self.client_addr)


class Server:
 def __init__(self, listen_port, target_addr):
  self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  self.sock.bind(('', listen_port))
  self.target_addr = target_addr
  self.run_thread = None
  self.timeout_thread = None
  self.conn_map = {}
  self.running = False

 def run(self):
  self.running = True
  self.run_thread = threading.Thread(target=self.handle_recv)
  self.run_thread.start()
  self.timeout_thread = threading.Thread(target=self.handle_timeout)
  self.timeout_thread.start()

 def close(self):
  self.running = False
  if self.run_thread is not None:
   while self.run_thread.is_alive():
    time.sleep(1)
  if self.timeout_thread is not None:
   while self.timeout_thread.is_alive():
    time.sleep(1)
  self.sock.close()

 def handle_recv(self):
  while self.running:
   readable, _, _ = select.select([self.sock, ], [], [], 1)
   if not readable:
    continue
   data, addr = self.sock.recvfrom(2048)
   conn = self.conn_map.get(addr)
   if conn:
    conn.send(data)
   else:
    print(f"new conn: {addr}")
    conn = Conn(addr, self.target_addr, self.send)
    conn.run()
    conn.send(data)
    self.conn_map[addr] = conn

 def send(self, data, client_addr):
  self.sock.sendto(data, client_addr)

 def handle_timeout(self):
  while self.running:
   for addr, conn in self.conn_map.copy().items():
    if time.time() - conn.last_active_time > CONN_TIMEOUT:
     conn.close()
     self.conn_map.pop(addr)
   time.sleep(1)


if __name__ == '__main__':
 args = sys.argv
 listen_port = None
 dst_ip = None
 dst_port = None
 if len(args) < 4:
  print("wrong args, use: <listen_port> <dst_ip> <dst_port>")
  sys.exit(1)
 try:
  listen_port = int(args[1])
  dst_ip = str(args[2]).encode('utf-8')
  dst_port = int(args[3])
 except Exception:
  print("wrong arg type")
  sys.exit(1)
 server = Server(listen_port, (dst_ip, dst_port))
 server.run()
 while True:
  try:
   time.sleep(1)
  except KeyboardInterrupt:
   print("terminating...")
   server.close()
   break

