import os, socket, select, struct, time, threading, random, math
from typing import List, Union, Tuple
from protobuf_decoder.protobuf_decoder import Parser
import blackboxprotobuf, copy, json, random, requests

def grcolor():
    top_colors = ["FFFF00", "FF0000", "00FF00", "87CEEB", "AAFF00"]
    random_color = random.choice(top_colors)
    return random_color

def parse_results(parsed_results):
    result_dict = {}
    for result in parsed_results:
        if result.field not in result_dict:
            result_dict[result.field] = []
        field_data = {}
        if result.wire_type in ["varint", "string", "bytes"]:
            field_data = result.data
        elif result.wire_type == "length_delimited":
            field_data = parse_results(result.data.results)
        result_dict[result.field].append(field_data)
    return {key: value[0] if len(value) == 1 else value for key, value in result_dict.items()}

def protobuf_dec(packet):
    parsed_results = Parser().parse(packet)
    return json.dumps(parse_results(parsed_results), ensure_ascii=False)

class messagedata:
    def __init__(self, data):
        self.valid = False
        try:
            decoded = json.loads(protobuf_dec(data.hex()[10:]))
            info = decoded.get("5", {})
            if not isinstance(info, dict):
                return None
            self.type = info.get("3")
            ClientId = info.get("2")
            PlayerId = info.get("1")

            if self.type == 1:
                ClientId = info["2"]
                PlayerId = info["1"]
            elif self.type == 2:
                ClientId = info["1"]
                PlayerId = info["1"]

            self.cid = ClientId
            self.uid = PlayerId
            self.name = info.get("9", {}).get("1", "")
            self.message = ("?/" if "8" in info else info.get("4", "")).lower()
            self.valid = True
        except Exception as e:
            self.cid = self.uid = self.name = self.message = self.type = None

def Encrypt(value: int) -> bytes:
    result = []
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)

def EncryptRepeated(values: list[int]) -> bytes:
    output = b""
    for v in values:
        output += Encrypt(v)
    return output

def create_varint_field(field_number, value):
    field_header = (field_number << 3) | 0
    return Encrypt(field_header) + Encrypt(value)

def create_length_delimited_field(field_number, value):
    field_header = (field_number << 3) | 2
    encoded_value = value.encode() if isinstance(value, str) else value
    return Encrypt(field_header) + Encrypt(len(encoded_value)) + encoded_value

def create_packed_repeated_field(field_number, values):
    packed_data = bytearray()
    for v in values:
        packed_data.extend(Encrypt(v))
    field_header = (field_number << 3) | 2
    return Encrypt(field_header) + Encrypt(len(packed_data)) + packed_data

def create_protobuf_packet(fields):
    packet = bytearray()
    for field, value in fields.items():
        if isinstance(value, dict):
            nested_packet = create_protobuf_packet(value)
            packet.extend(create_length_delimited_field(field, nested_packet))
        elif isinstance(value, list):
            if all(isinstance(x, int) for x in value):
                packet.extend(create_packed_repeated_field(field, value))
            else:
                for item in value:
                    if isinstance(item, int):
                        packet.extend(create_varint_field(field, item))
                    elif isinstance(item, str) or isinstance(item, bytes):
                        packet.extend(create_length_delimited_field(field, item))
                    elif isinstance(item, dict):
                        nested_packet = create_protobuf_packet(item)
                        packet.extend(create_length_delimited_field(field, nested_packet))
        elif isinstance(value, int):
            packet.extend(create_varint_field(field, value))
        elif isinstance(value, str) or isinstance(value, bytes):
            packet.extend(create_length_delimited_field(field, value))
    return packet

def player_id_login(uid):
    url = "https://napthe.vn/api/auth/player_id_login"
    
    # Payload
    payload = {
        "app_id": 100067,
        "login_id": str(uid),
        "app_server_id": 0x000,
    }

    print("\n==================== PLAYER_ID_LOGIN ====================")
    print("[PAYLOAD DICT]")
    print(payload)

    payload_json = json.dumps(payload)
    print("\n[PAYLOAD JSON]")
    print(payload_json)

    # Headers
    headers = {
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept": "application/json",
        "Referer": "https://napthe.vn/app/100067/idlogin",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36",
        "Cookie": "datadome=9SKY0NQDmJskwyYecdQm4AwRLX5Cw6QGHXVojTXdB9zyO2XqhZi3yP6FPDZ8tBTHxKwCLlIYRUL35e_XKcYDT4Sr3shME1ZypsukSWpj0rHxPX6fzlfg242Azyw3wIjQ",
    }

    print("\n[HEADERS]")
    print(headers)

    try:
        # Gửi request
        resp = requests.post(url, data=payload_json, headers=headers, timeout=10)

        print("\n[STATUS CODE]")
        print(resp.status_code)

        print("\n[RESPONSE HEADERS]")
        try:
            print(dict(resp.headers))
        except Exception:
            print(resp.headers)

        print("\n[RAW RESPONSE TEXT]")
        print(resp.text)

        # Parse JSON
        try:
            data = resp.json()
        except Exception as e:
            print("\n[ERROR PARSING JSON]")
            print(e)
            return None

        print("\n[PARSED JSON]")
        print(data)

        nickname = data.get("nickname")
        print("\n[NICKNAME]")
        print(nickname)
        print("=========================================================\n")

        return nickname

    except Exception as e:
        print("\n[REQUEST ERROR]")
        print(e)
        print("=========================================================\n")
        return None

def reply(cid, chatType, message):
    fields = {}
    fields[1] = int(cid)
    fields[2] = int(18)
    fields[4] = int(2)
    fields[5] = {}
    fields[5][1] = 234084744
    fields[5][2] = int(cid)
    if chatType:
        fields[5][3] = int(chatType)
    fields[5][4] = str(message)
    fields[5][9] = {}
    fields[5][9][1] = "[b] : [FF0000]@[FF4500]S[FFA500]I[FFFF00]B[00FF00]I[00FFFF]D[0000FF]I[8A2BE2]_[FF00FF]T[FF1493]o[FF69B4]lét"
    fields[5][9][2] = 902000207
    fields[5][9][10] = 0x1
    fields[5][9][13] = {}
    fields[5][9][13][1] = 2
    fields[5][9][14] = {}
    fields[5][9][14][2] = 8
    fields[5][9][14][3] = bytes([16,21,8,10,11,19,12,15,17,4,7,2,3,13,14,18,1,5,6])

    def sfield(d):
        return {
            k: sfield(v) if isinstance(v, dict) else v
            for k, v in sorted(
                d.items(),
                key=lambda x: int(x[0]) if str(x[0]).isdigit() else x[0],
            )
        }

    packet = create_protobuf_packet(sfield(fields)).hex()
    length = hex(len(packet) // 2)[2:]
    packet = "12" + ("0" * (8 - len(length))) + length + packet
    return bytes.fromhex(packet)

def GenAddItem(Items):
    All_items = []
    for ItemId in Items:
        Item = {}
        Item[1] = int(ItemId)
        Item[2] = int(1)
        All_items.append(Item)
    Fields = {}
    Fields[1] = int(1)
    Fields[2] = int(8)
    Fields[4] = int(6)
    Fields[5] = {}
    Fields[5][1] = All_items
    packet = create_protobuf_packet(Fields).hex()
    packet = "08000000" + Encrypt(len(packet) // 2).hex() + packet
    return bytes.fromhex(packet)

def ModifySquadPacket(packet: str, uid: int, type: int = 1) -> bytes:
    def animation_group(packet: str, aid: list[int]):
        buf = bytes.fromhex(packet[10:])
        message, typedef = blackboxprotobuf.decode_message(buf)
        Fields = message["5"]["6"]
        Fields["15"] = EncryptRepeated(aid)
        typedef["5"]["message_typedef"]["6"]["message_typedef"]["15"] = {
            "name": "",
            "type": "bytes",
        }
        packet_inner = blackboxprotobuf.encode_message(message, typedef)
        return packet_inner

    def copy_squad(packet: str, mid: int):
        buf = bytes.fromhex(packet[10:])
        message, typedef = blackboxprotobuf.decode_message(buf)
        ORIG_OBJ = message["5"]["6"]
        ORIG_NAE = ORIG_OBJ["2"]
        COPI_OBJ = copy.deepcopy(ORIG_OBJ)
        COPI_OBJ["1"] = int(mid)
        COPI_OBJ["2"] = str("[FF0000]%s" % str(ORIG_NAE.decode("utf-8")))
        if "75" in COPI_OBJ and isinstance(COPI_OBJ["75"], dict):
            COPI_OBJ["75"]["1"] = int(mid)
        else:
            COPI_OBJ["75"] = {"1": int(mid)}
        message["5"]["6"] = [ORIG_OBJ, COPI_OBJ]
        message["4"] = 6
        if "5" in typedef and "message_typedef" in typedef["5"]:
            typedef["5"]["message_typedef"]["2"]["repeated"] = True
        packet_inner = blackboxprotobuf.encode_message(message, typedef)
        return packet_inner

    if type == 1:
        packet_inner = copy_squad(packet, uid).hex()
    else:
        packet_inner = animation_group(packet, uid).hex()
    packet_final = "0500000" + hex(len(packet_inner) // 2)[2:] + packet_inner
    return bytes.fromhex(packet_final)

def GenDiamondPacket(gold: int, diamond: int):
    Fields = {}
    Fields[1] = int(7)
    Fields[2] = int(8)
    Fields[4] = int(2)
    Fields[5] = {}
    if Fields:
        Fields[5][1] = gold
        Fields[5][2] = diamond
        Fields[5][3] = 200
    packet = create_protobuf_packet(Fields).hex()
    packet = "08000000" + Encrypt(len(packet) // 2).hex() + packet
    return bytes.fromhex(packet)

def GenEmotePacket(clientId, EmoteId):
    Fields = {}
    Fields[1] = int(clientId)
    Fields[2] = int(5)
    Fields[4] = int(22)
    Fields[5] = {}
    Fields[5][1] = int(clientId)
    Fields[5][2] = int(EmoteId)
    Fields[5][5] = {}
    Fields[5][5][1] = int(clientId)
    Fields[5][5][3] = int(EmoteId)
    packet = create_protobuf_packet(Fields).hex()
    packet = "05000000" + Encrypt(len(packet) // 2).hex() + packet
    return bytes.fromhex(packet)

def GenAddFriendsPacket(uid, nickname):
    fields = {
        1: 234084744,
        2: 6,
        4: 2,
        5: {
            1: int(uid),
            3: "[FF0033]".format(nickname),
            6: "VN",
            8: 100,
            22: 20,
            23: 128,
            27: 901027033,
            28: 902027027,
            30: 1,
            31: 128,
            34: 1,
            42: 10,
            43: 33,
        },
    }
    packet = create_protobuf_packet(fields).hex()
    packet = "05000000" + Encrypt(len(packet) // 2).hex() + packet
    return bytes.fromhex(packet)

class socks5:
    MainC = None
    MainR = None
    UID = None

    @classmethod
    def set(cls, client, remote):
        cls.MainC, cls.MainR = client, remote

    @classmethod
    def send(cls, packet):
        if cls.MainC:
            cls.MainC.send(packet)
            return True
        return False

def FltText(text: str):
    Fields = {}
    Fields[1] = 0x001
    Fields[2] = 5
    Fields[4] = 50
    Fields[5] = {}
    Fields[5][1] = 0x01
    Fields[5][2] = str(text)
    Fields[5][3] = 0x1
    packet = create_protobuf_packet(Fields).hex()
    packet = "05000000" + hex(len(packet) // 2)[2:] + packet
    return bytes.fromhex(packet)

class SOCKS5_SERVER:
    def __init__(self):
        self.squadpacket = None
        self.dltids = [1923378310, 234084744, 156493720]
        self.aid = 912050001
        self.isanimation_group = True
        self.socks1200 = None

    def client_connect(self, cnn, sport, saddr):
        remote = None

        def verify_if_gay():
            version = cnn.recv(1)[0]
            cnn.recv(cnn.recv(1)[0]).decode()
            cnn.recv(cnn.recv(1)[0]).decode()
            cnn.sendall(bytes([version, 0x00]))
            return True

        version, nmethods = cnn.recv(2)
        methods = set(cnn.recv(nmethods))
        if 0x00 in methods:
            cnn.sendall(bytes([0x05, 0x00]))
        elif 0x02 in methods:
            cnn.sendall(bytes([0x05, 0x02]))
            verify_if_gay()
        else:
            cnn.sendall(bytes([0x05, 0xFF]))
            cnn.close()
            return False
        try:
            version, dev, s, addr_type = cnn.recv(4)
            if addr_type == 1:
                address = socket.inet_ntoa(cnn.recv(4))
            elif addr_type == 3:
                address = cnn.recv(cnn.recv(1)[0]).decode()
            else:
                cnn.close()
                return False

            port = int(cnn.recv(2).hex(), 16)
            if dev == 1:
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.connect((address, port))
                sockname = remote.getsockname()
                addr = int.from_bytes(socket.inet_aton(sockname[0]), "big")
                cnn.send(struct.pack("!BBBBIH", 5, 0, 0, 1, addr, sockname[1]))
                self.server(cnn, remote, port)
            else:
                cnn.send(struct.pack("!BBBBIH", 5, 7, 0, 1, 0, 0))
                cnn.close()
        except Exception:
            cnn.close()

    def connect(self, host="0.0.0.0", port=1080):
        try:
            print(host, port)
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind((host, port))
            server.listen(10)
            while True:
                cnn, adr = server.accept()
                threading.Thread(
                    target=self.client_connect,
                    args=(cnn, port, adr),
                    daemon=True,
                ).start()
        except Exception:
            server.close()

    def SENDNOTIAFTERLOGIN(self):
        time.sleep(7)
        socks5.send(FltText("\n[AAFF00]LOGIN SUCCESS[000000]\n"))
        time.sleep(3)
        noti = """[b]\n[%s]Dịch vụ: [FFFFFF][U]LIKES - BOT - API - UID.[/U][%s]
Telegram[FFFFFF]: [00FFFF]@ [FFFFFF]& [%s]TikTok[FFFFFF]: [00FFFF]\n[000000]""" % (
            grcolor(),
            grcolor(),
            grcolor(),
        )
        socks5.send(FltText(noti))

    def server(self, client, remote, port):
        while True:
            try:
                gringo, gay, dev = select.select(
                    [client, remote], [], [client, remote], 0x5
                )
                if client in gringo:
                    if not self.recvdataC(client, remote, port):
                        break
                if remote in gringo:
                    if not self.recvdataS(client, remote, port):
                        break
            except Exception as e:
                print(e)

    def recvdataS(self, client, remote, port):
        try:
            dataS = remote.recv(12345)
        except Exception:
            return False
        if client.send(dataS) <= 0:
            client.close()
            remote.close()
            return False
        hexdata = dataS.hex()
        if hexdata.startswith("0500") and "10052001" in hexdata:
            self.squadpacket = hexdata
            if self.isanimation_group:
                socks5.send(ModifySquadPacket(hexdata, [int(self.aid)], 2))
            if self.socks1200:
                self.socks1200.send(
                    reply(
                        socks5.UID,
                        None,
                        """[0066FF][b]           
[0099FF]--------------------------------------

[00CCFF]Fake bạn bè trong ds
[99FFFF]   /fake:bb:%uid

[00CCFF]Fake quân đoàn
[99FFFF]   /fake:qd:%x

[00CCFF]Fake kim cương & vàng (max)
[99FFFF]   /fake:kc

[0099FF]-------------------------------------- ( bảo trì )

[00CCFF]Bật hành động bất kì = id
[99FFFF]   /play:%eid

[00CCFF]Hành động theo OB
[99FFFF]   /e:e01:AK47 (Full HD nâng cấp)
[99FFFF]   /e:e02:%x (HD OB45)
[99FFFF]   /e:e03:%x (HD OB46)
[99FFFF]   /e:e04:%x (HD OB47)
[99FFFF]   /e:e05:%x (HD OB48)
[99FFFF]   /e:e06:%x (HD OB49)
[99FFFF]   /e:e07:%x (HD OB50)

[00CCFF]Bật hành động cho tất cả người trong team
[99FFFF]   /all:AK47

[0099FF]--------------------------------------

[00CCFF][b]Chuyển động nhóm
[99FFFF]   /set:cd:[33FFFF]true[99FFFF]/[33FFFF]false[99FFFF] ([FFFFFF]default=[33FFFF]true[99FFFF])
[99FFFF]   /set:cd:%x (đổi chuyển động)

[00CCFF]Unlock all skin (outfit)
[99FFFF]   /skin

[00CCFF]Tạo bản sao của mày trong team
[99FFFF]   /me
""",
                    )
                )

        if hexdata.startswith("1200") and int(port) in [39800, 39801]:
            threading.Thread(target=self.gringay, args=(client, dataS)).start()
        return True

    def recvdataC(self, client, remote, port):
        dataC = client.recv(12345)
        if remote.send(dataC) <= 0:
            client.close()
            remote.close()
            return False
        hexdata = dataC.hex()
        if (
            hexdata.startswith("01")
            and int(port) in [39699, 39698]
            and len(dataC) > 666
        ):
            extrac_uid = lambda packet: int(packet[4:20].lstrip("0"), 16)
            socks5.UID = int(extrac_uid(hexdata))
            threading.Thread(target=self.SENDNOTIAFTERLOGIN).start()
        if int(port) in [39698, 39699]:
            socks5.set(client, remote)
        if int(port) in [39800, 39801]:
            self.socks1200 = client
        return True

    def gringay(self, client, recv):
        data = messagedata(recv)
        if not data.valid:
            return False
        if data.type in [5]:
            return False
        uid, cid, type_ = data.uid, data.cid, data.type
        message, name = data.message, data.name

        # /help
        if message.startswith("/help"):
            client.send(reply(cid, type_, "[0066FF][b]      Danh sách các lệnh"))
            client.send(
                reply(
                    cid,
                    type_,
                    """[0066FF][b]           
[0099FF]--------------------------------------

[00CCFF]Fake bạn bè trong ds
[99FFFF]   /fake:bb:%uid

[00CCFF]Fake quân đoàn
[99FFFF]   /fake:qd:%x

[00CCFF]Fake kim cương & vàng (max)
[99FFFF]   /fake:kc

[0099FF]-------------------------------------- ( bảo trì )

[00CCFF]Bật hành động bất kì = id
[99FFFF]   /play:%eid

[00CCFF]Hành động theo OB
[99FFFF]   /e:e01:AK47 (Full HD nâng cấp)
[99FFFF]   /e:e02:%x (HD OB45)
[99FFFF]   /e:e03:%x (HD OB46)
[99FFFF]   /e:e04:%x (HD OB47)
[99FFFF]   /e:e05:%x (HD OB48)
[99FFFF]   /e:e06:%x (HD OB49)
[99FFFF]   /e:e07:%x (HD OB50)

[00CCFF]Bật hành động cho tất cả người trong team
[99FFFF]   /all:AK47

[0099FF]--------------------------------------

[00CCFF][b]Chuyển động nhóm
[99FFFF]   /set:cd:[33FFFF]true[99FFFF]/[33FFFF]false[99FFFF] ([FFFFFF]default=[33FFFF]true[99FFFF])
[99FFFF]   /set:cd:%x (đổi chuyển động)

[00CCFF]Unlock all skin (outfit)
[99FFFF]   /skin

[00CCFF]Tạo bản sao của mày trong team
[99FFFF]   /me
""",
                )
            )
            return True

        # /fake
        if message.startswith("/fake"):
            value = message.split(":")
            if len(value) < 2:
                pass
            else:
                cmd = value[1]
                if cmd == "bb":
                    if len(value) < 3:
                        client.send(reply(cid, type_, "[FF0000]Thiếu ID"))
                    else:
                        nickname = player_id_login(value[2])
                        if nickname is None:
                            client.send(reply(cid, type_, "ID SAI"))
                        else:
                            socks5.send(GenAddFriendsPacket(value[2], nickname))
                            client.send(
                                reply(
                                    cid,
                                    type_,
                                    "[AAFF00]Added '%s' to friend list" % nickname,
                                )
                            )
                elif cmd == "kc":
                    client.send(reply(cid, type_, "[AAFF00]Added diamond & gold"))
                    for i in range(5, 10):
                        vg = random.randint(10 ** (i - 1), 10**i - 1)
                        kc = random.randint(vg, 10**i - 1)
                        socks5.send(GenDiamondPacket(vg, kc))
                        time.sleep(1.3)
                    value_max = 0x3B9AC9FF
                    socks5.send(GenDiamondPacket(value_max, value_max))
                else:
                    client.send(reply(cid, type_, "[FF0000]INVALID"))

        elif message.startswith("/set"):
            value = message.split(":")
            if len(value) < 2:
                pass
            else:
                if value[1] == "cd":
                    if value[2] == "true":
                        self.isanimation_group = True
                    elif value[2] == "false":
                        self.isanimation_group = False
                    elif int(value[2]) in [1, 2, 3, 4, 5]:
                        idx = int(value[2])
                        if idx == 1:
                            self.aid = 912049001
                        elif idx == 2:
                            self.aid = 912050002
                        elif idx == 3:
                            self.aid = 912048001
                        elif idx == 4:
                            self.aid = 912038002
                        elif idx == 5:
                            self.aid = 912050001
                        else:
                            client.send(reply(cid, type_, "[FF0000]INVALID"))
                    else:
                        client.send(reply(cid, type_, "[AAFF00]MAX 5"))
                    client.send(reply(cid, type_, "[FF0000]Done"))
                else:
                    client.send(reply(cid, type_, "[FF0000]INVALID"))

        elif message.startswith("/e"):
            value = message.split(":")
            if len(value) < 2:
                pass
            else:
                sub = value[1]
                if sub == "e01":
                    Emotes = {
                        "AK47": 909000063,
                    "MP40": 909000075,
                    "MP40v2": 909040010,
                    "P90": 909049010,
                    "SCAR": 909000068,
                    "UMP": 909000098,
                    "MP5": 909033002,
                    "XM8": 909000085,
                    "M4A1": 909033001,
                    "M1887": 909035007,
                    "LEVEL100": 909042007,
                    "M1014": 909000081,
                    "GROZA": 909041005,
                    "M1014V2": 909039011,
                    "G18": 909038012,
                    "THOMPSON": 909038010
                    }
                    if len(value) < 3:
                        elist = ", ".join(e for e in Emotes)
                        client.send(reply(cid, type_, "[AAFF00]EMOTE --> DONE" ))
                    else:
                        vl = value[2].upper()
                        if vl in Emotes:
                            if not cid:
                                client.send(
                                    reply(
                                        cid, type_, "[AAFF00]Không lấy dc uid"
                                    )
                                )
                                return False
                            socks5.send(GenEmotePacket(cid, Emotes[vl]))
                            client.send(
                                reply(
                                    cid,
                                    type_,
                                    "[AAFF00]EMOTE --> DONE" ,
                                )
                            )
                        else:
                            elist = ", ".join(e for e in Emotes)
                            client.send(reply(cid, type_, "[AAFF00]%s" % elist))
                elif sub in ("e02", "e03", "e04", "e05", "e06", "e07", "e08"):
                    if len(value) < 3:
                        client.send(reply(cid, type_, "[FF0000]Thiếu tham số"))
                    else:
                        EmoteId = int(
                            "9090%02d%03d" % (43 + int(sub[2:]), int(value[2]))
                        )
                        socks5.send(GenEmotePacket(cid, EmoteId))
                        client.send(
                            reply(
                                cid,
                                type_,
                                "[AAFF00]EMOTE --> DONE" ,
                            )
                        )
                else:
                    client.send(reply(cid, type_, "[FF0000]INVALID"))

        elif message.startswith("/me"):
            for c, duid in enumerate(self.dltids, start=1):
                socks5.send(ModifySquadPacket(self.squadpacket, duid, 0x1))
                client.send(
                    reply(cid, type_, "[AAFF00]ADD [FFFFFF]--> [AAFF00]%s" % c)
                )
                time.sleep(1)

        elif message.startswith("/skin"):
            def ADD_ITEMS():
                import ast
                import os
                import time

                # Lấy đường dẫn file items.list trong cùng thư mục với file .py này
                base_dir = os.path.dirname(os.path.abspath(__file__))
                items_file = os.path.join(base_dir, "items.list")

                # Đọc dữ liệu từ file
                with open(items_file, "r", encoding="utf-8") as f:
                    data = ast.literal_eval(f.read())

                # Giữ nguyên logic chia 11 phần như cũ
                for i in range(0, len(data), 11):
                    items = data[i:i+11]
                    socks5.send(GenAddItem(items))
                    time.sleep(0.05)

            # chạy thread xử lý items
            threading.Thread(target=ADD_ITEMS).start()
            client.send(reply(cid, type_, "[AAFF00]ITEMS ADDED"))
            time.sleep(1)

        elif message.startswith("/play"):
            parts = message.split(":")
            if len(parts) < 2:
                client.send(reply(cid, type_, "INVALID ID"))
            else:
                if parts[1].startswith("9090"):
                    eid = int(parts[1])
                    if not socks5.UID:
                        client.send(
                            reply(cid, type_, "[AAFF00]Không lấy dc uid")
                        )
                        return False
                    socks5.send(GenEmotePacket(cid, eid))
                    client.send(
                        reply(
                            cid,
                            type_,
                            "[AAFF00]EMOTE [FFFFFF]--> [AAFF00]%s" % eid,
                        )
                    )
                else:
                    client.send(
                        reply(
                            cid,
                            type_,
                            "INVALID ID, Emote id phải bắt đầu bằng 9090",
                        )
                    )

        elif message.startswith("/all"):
            parts = message.split(":")
            if len(parts) < 2:
                client.send(reply(cid, type_, "[FF0000]/all:ak47 mp40 mp40v2 p90 scar ump mp5 xm8 m4a1 m1887 level100 m1014 groza m1014v2 g18 thompson "))
            else:
                value = parts[1].upper()
                Emotes = {
                    "AK47": 909000063,
                    "MP40": 909000075,
                    "MP40v2": 909040010,
                    "P90": 909049010,
                    "SCAR": 909000068,
                    "UMP": 909000098,
                    "MP5": 909033002,
                    "XM8": 909000085,
                    "M4A1": 909033001,
                    "M1887": 909035007,
                    "LEVEL100": 909042007,
                    "M1014": 909000081,
                    "GROZA": 909041005,
                    "M1014V2": 909039011,
                    "G18": 909038012,
                    "THOMPSON": 909038010
                    
                }
                if value in Emotes:
                    emid = Emotes[value]
                    socks5.send(GenEmotePacket(cid, emid))
                    for duid in self.dltids:
                        socks5.send(GenEmotePacket(duid, emid))
                    client.send(
                        reply(
                            cid,
                            type_,
                            "[AAFF00]EMOTE --> DONE" ,
                        )
                    )
                else:
                    client.send(reply(cid, type_, "[FF0000]INVALID"))

        return True

if __name__ == "__main__":
    SS = SOCKS5_SERVER()
    for port in [1304]:
        threading.Thread(target=SS.connect, args=("0.0.0.0", port)).start()