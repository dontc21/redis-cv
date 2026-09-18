import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost',6380))


while True:
    cmd = input(">")  #从键盘输入
    if cmd.strip().upper() == "EXIT":
        break

    client.sendall((cmd + "\r\n").encode()) #把输入的字符串编码成字节再发
    data = client.recv(1024)


    print("收到",data)

    
client.close()