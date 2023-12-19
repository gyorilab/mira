import requests
import io


class MDL:
    def __init__(self):
        pass


# mld based off model described here: https://metasd.com/2020/03/steady-state-growth-sir-seir-models/
URL = "https://metasd.com/wp-content/uploads/2020/03/SEIR-SS-growth3.mdl"
if __name__ == "__main__":
    data = requests.get(URL).content

    f = io.BytesIO(data)

    l = f.readlines()

    for k in l:
        print(k)
        print()
