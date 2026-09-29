import socket
import threading
import time



server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('localhost',6380))
server.listen()

print("等待连接")

store = {}

lock = threading.Lock()  #全局锁





def is_expired(key):
    if key not in store:
        return True   #表示已经过期或者不存在
    _, expire_at = store[key]   # 元组 value ，expire_at ，这个_表示不需要但必须要接收
    if expire_at is not None and time.time() > expire_at:
        del store[key]
        return True
    return False

AOF_LIFE = "appendonly.aof"

def log_command(line):
    with open(AOF_LIFE, "a") as f:
        f.write(line + "\n")


def load_aof():
    """服务器启动时，重放 AOF 日志恢复数据"""

    try:
        with open(AOF_LIFE, "r") as f:
            for line in f:

                line = line.strip()

                if not line:
                    continue

                parts = line.split()
                cmd = parts[0].upper()

                if cmd == "SET":
                    key, value = parts[1], parts[2]

                    expire_at = None

                    # AOF 中保存的是绝对过期时间
                    if len(parts) >= 5 and parts[3].upper() == "EXAT":
                        expire_at = float(parts[4])

                    # 情况1：没有过期时间
                    if expire_at is None:
                        store[key] = (value, expire_at)

                    # 情况2：有过期时间，并且现在还没有过期
                    elif time.time() < expire_at:
                        store[key] = (value, expire_at)

                    # 情况3：有过期时间，但是已经过期
                    else:
                        # 防止这个 key 之前的旧值复活
                        if key in store:
                            del store[key]

                        continue

                elif cmd == "DEL":
                    key = parts[1]

                    if key in store:
                        del store[key]
    except FileNotFoundError:
        pass #第一次启动，日志无，也属于无误情况


def handle_client(coon, addr):
    
    print(f"{addr}连接成功")

    
    buffer = ""

    while True:
        data = coon.recv(1024)

        if not data:
            coon.close()
            break
            

        buffer += data.decode()

        while "\r\n" in buffer:
            line, buffer = buffer.split("\r\n",1)
            if not line:
                continue
            print("收到命令",line)
        
            parts = line.split()
            cmd = parts[0].upper() if parts else ""

            if cmd == "PING":
                coon.sendall(b"+PONG\r\n")

            elif cmd == "SET":
                key, value = parts[1], parts[2]

                expire_at = None
                if len(parts) >= 5 and parts[3].upper() == "EX":  #SET NAME TAKS EX 20  ex是固定模板
                    expire_at = time.time() + int(parts[4])  #当前时间加多少s后过期

                with lock:
                    store[key] = (value, expire_at)
                    if expire_at is not None:
                        log_command(f"SET {key} {value} EXAT {expire_at}")
                    else:
                        log_command(f"SET {key} {value}")
                coon.sendall(b"+OK\r\n")

            elif cmd == "GET":
                key = parts[1]
                with lock:
                    if is_expired(key):
                        coon.sendall(b"$-1\r\n")
                    else:
                        value, _ = store[key]
                        coon.sendall(f"+{value}\r\n".encode())

            elif cmd == "DEL":
                key = parts[1]
                with lock:
                    if is_expired(key):
                        coon.sendall(b":0\r\n")
                    else:
                        del store[key]
                        log_command(line)
                        coon.sendall(b":1\r\n")

            elif cmd == "EXISTS":
                key = parts[1]
                with lock:
                    if is_expired(key):
                        coon.sendall(b":0\r\n")
                    else:
                        coon.sendall(b":1\r\n")

            elif cmd == "KEYS":
                with lock:
                    valid_keys = [k for k in list(store.keys()) if not is_expired(k)]
                    if not valid_keys:
                        coon.sendall(b"*0\r\n")
                    else:
                        response = f"*{len(valid_keys)}\r\n"
                        for k in valid_keys:
                            response += f"${len(k)}\r\n{k}\r\n"
                        coon.sendall(response.encode())
                        

            else:
                coon.sendall(b"-ERR unknown command")


load_aof()
print(" 等待连接")

while True:
    
    coon,addr = server.accept()
    t = threading.Thread(target=handle_client, args=(coon, addr))
    t.start()





