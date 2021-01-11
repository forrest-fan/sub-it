import pickle
import os
import json

# JSON data scraped from https://healabel.com/carbon-footprint-of-foods

# opens the .json folder that stores the alternate ingredients
with open("./alt_ingr.json", 'r') as fp:
    alt_ingr = json.load(fp)

with open("./ingr_co2.json", 'r') as fp:
    ingr_co2 = json.load(fp)

def findAlts(ingredients):
    alts = []
    altsFound = []
    for ing in ingredients:
        for word in ing.split():
            if (alt_ingr.get(word) is not None) and (len(alt_ingr[word]) is not 0) and (word not in altsFound):
                min = float('inf')
                min_food = ""
                print(word)
                for ingr, co2 in alt_ingr[word]:
                    if co2 < min:
                        min = co2
                        min_food = ingr
                alts.append({
                    "food": word,
                    "alternative": min_food,
                    "savings": round(ingr_co2[word] - min, 2)
                })
                altsFound.append(word)
    return alts