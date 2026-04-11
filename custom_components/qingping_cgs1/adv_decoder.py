# adv_decoder.py

from __future__ import annotations

from typing import Any


def decode_qingping_adv_data(adv_hex: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "temperature": None,
        "humidity": None,
        "battery": None,
        "payload_mac": None,
    }

    try:
        raw = bytes.fromhex(adv_hex)
    except ValueError:
        return result

    i = 0
    while i < len(raw):
        if i + 1 >= len(raw):
            break

        ad_len = raw[i]
        if ad_len == 0:
            break

        end = i + 1 + ad_len
        if end > len(raw):
            break

        ad_type = raw[i + 1]
        ad_payload = raw[i + 2:end]

        # 0x16 = Service Data, 16-bit UUID
        if ad_type == 0x16 and len(ad_payload) >= 2:
            uuid_hex = ad_payload[:2][::-1].hex().upper()

            # Qingping/Cleargrass service UUID
            if uuid_hex == "FDCD":
                body = ad_payload[2:]

                # 2 bytes header + 6 bytes MAC + TLV
                if len(body) < 8:
                    return result

                mac_reversed = body[2:8]
                tlv = body[8:]

                result["payload_mac"] = mac_reversed[::-1].hex().upper()

                j = 0
                while j + 2 <= len(tlv):
                    t = tlv[j]
                    l = tlv[j + 1]
                    v_start = j + 2
                    v_end = v_start + l
                    if v_end > len(tlv):
                        break

                    v = tlv[v_start:v_end]

                    # 0x01 len=4 -> temp + humidity
                    if t == 0x01 and l == 4:
                        result["temperature"] = int.from_bytes(v[0:2], "little") / 10.0
                        result["humidity"] = int.from_bytes(v[2:4], "little") / 10.0

                    # 0x02 len=1 -> battery
                    elif t == 0x02 and l == 1:
                        result["battery"] = v[0]

                    j = v_end

                result["ok"] = True
                return result

        i = end

    return result