import requests

response = requests.post("http://127.0.0.1:8000/optimize-plates", json={
    "tags": [
        {"COLOR": "812 GREY VIGO", "SIZE": "XXS", "QTY": 60},
        {"COLOR": "800 BLACK", "SIZE": "XXS", "QTY": 72},
        {"COLOR": "676 ROSA EMPO", "SIZE": "XXS", "QTY": 96},
        {"COLOR": "812 GREY VIGO", "SIZE": "XL", "QTY": 121},
        {"COLOR": "800 BLACK", "SIZE": "XL", "QTY": 145},
        {"COLOR": "676 ROSA EMPO", "SIZE": "XL", "QTY": 193},
        {"COLOR": "812 GREY VIGO", "SIZE": "XS", "QTY": 337},
        {"COLOR": "812 GREY VIGO", "SIZE": "L", "QTY": 366},
        {"COLOR": "800 BLACK", "SIZE": "XS", "QTY": 407},
        {"COLOR": "800 BLACK", "SIZE": "L", "QTY": 439},
        {"COLOR": "676 ROSA EMPO", "SIZE": "XS", "QTY": 540},
        {"COLOR": "676 ROSA EMPO", "SIZE": "L", "QTY": 586},
        {"COLOR": "812 GREY VIGO", "SIZE": "M", "QTY": 833},
        {"COLOR": "812 GREY VIGO", "SIZE": "S", "QTY": 883},
        {"COLOR": "800 BLACK", "SIZE": "M", "QTY": 999},
        {"COLOR": "800 BLACK", "SIZE": "S", "QTY": 1059},
        {"COLOR": "676 ROSA EMPO", "SIZE": "M", "QTY": 1333},
        {"COLOR": "676 ROSA EMPO", "SIZE": "S", "QTY": 1412}
    ],
    "upsPerPlate": 20,
    "plateCount": 3
})

try:
    print(response.json())
except Exception as e:
    print("Server response was not JSON!")
    print("Status code:", response.status_code)
    print("Text:", response.text)
