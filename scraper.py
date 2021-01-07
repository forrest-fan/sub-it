import pickle
import os
import numpy as np
import random
import requests
from bs4 import BeautifulSoup
from collections import defaultdict


def parse_co2():
    co2_def_dict = defaultdict(list)

    url = "https://healabel.com/carbon-footprint-of-foods"
    page = requests.get(url).text
    soup = BeautifulSoup(page, "lxml")
    ids = ["block-yui_3_17_2_1_1556431745228_154502", "block-yui_3_17_2_1_1556431745228_512027",
           "block-yui_3_17_2_1_1556274452845_143799", "block-yui_3_17_2_1_1556431745228_536047",
           "block-yui_3_17_2_1_1556431745228_620052", "block-yui_3_17_2_1_1556431745228_692551",
           "block-yui_3_17_2_1_1556431745228_679394", "block-yui_3_17_2_1_1556431745228_634445",
           "block-yui_3_17_2_1_1556431745228_603856"]
    for block in ids:
        text = [p.text for p in soup.find(id=block).find('div').find('ul').find_all('li')]
        for sentence in text:
            food_split = sentence.split(",")
            food = food_split[0]
            if "(" in food:
                food = food.split("(")[0]

            co2 = sentence.split("CO2e")[0]
            co2 = co2.split(",")[-1]
            co2 = co2.replace("kg", "")
            co2 = co2.strip()

            if len(co2.split(" ")) >= 2:
                co2 = co2.split(" ")[-1]

            if "-" in co2:
                co2 = co2.split("-")[0]

            co2_def_dict[food].append(float(co2))

    ## if there are multiple values for one food, take the mean
    co2_dict = {k: np.mean(v_list) for k, v_list in co2_def_dict.items()}

    return co2_dict


def build_ingridient_maps():

    np.random.seed(1234)
    random.seed(1234)

    co2_dict = parse_co2()

    data_dir = "/data"
    print(os.path.join(data_dir, "ingr_vocab.pkl"))
    ingrs_vocab = pickle.load(open(os.path.join(data_dir, "ingr_vocab.pkl"), "rb"))
    print(ingrs_vocab)
    ingr_co2_map = {}

    for ingr in ingrs_vocab:
        if "<" not in ingr:
            # ingr_co2_map[ingr] = np.max(0.0, (np.random.randn() + 2.0) * 2.0)
            rnd_val = (np.random.randn() + 1.0) * 2
            if rnd_val < 0.0:
                rnd_val = np.random.rand()
            ingr_co2_map[ingr] = rnd_val

            if (
                "beef" in ingr
                or "pork" in ingr
                or "meat" in ingr
                or "pig" in ingr
                or "duck" in ingr
                or "chick" in ingr
                or "lamb" in ingr
                or "cow" in ingr
                or "wurst" in ingr
                or "bird" in ingr
                or "deer" in ingr
            ):
                ingr_co2_map[ingr] = ingr_co2_map[ingr] * np.random.randint(3, 10)

            for parsed_food in co2_dict:
                if parsed_food in ingr:
                    ingr_co2_map[ingr] = co2_dict[parsed_food]
                    #print(f"Found match: {parsed_food} - {ingr}")

            #print(ingr, ingr_co2_map[ingr])

    with open(os.path.join(data_dir, "ingr_co2.pkl"), "wb") as pf_:
        pickle.dump(ingr_co2_map, pf_)

    low_foods = {ingr: val for ingr, val in ingr_co2_map.items() if val < 1.5}

    ingr_alternatives = defaultdict(list)

    for ingr in ingrs_vocab:
        if "<" not in ingr and ingr_co2_map[ingr] > 3.0:
            for i in range(np.random.randint(1, 4)):
                alt_ingr = random.choice(list(low_foods.keys()))
                ingr_alternatives[ingr].append((alt_ingr, ingr_co2_map[alt_ingr]))

        print(ingr, ingr_alternatives[ingr])

    with open(os.path.join(data_dir, "ingr_alt.pkl"), "wb") as pf_:
        pickle.dump(ingr_alternatives, pf_)


if __name__ == "__main__":
    build_ingridient_maps()