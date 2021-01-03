import pickle
import os
import json

# opens the .json folder that stores the alternate ingredients
with open("./alt_ingr.json", 'r') as fp:
    alt_ingr = json.load(fp)

def findAlts(ingredients):
    alts = []
    for ing in ingredients:
        print(ing)
        for word in ing.split():
            print(word)
            if alt_ingr.get(word) is not None and len(alt_ingr[word]) is not 0:
                print('found')
                min = float('inf')
                min_food = ""
                for ingr, co2 in alt_ingr[word]:
                    if co2 < min:
                        min = co2
                        min_food = ingr
                alts.append({
                    "food": word,
                    "alternative": min_food,
                    "savings": min
                })
    return alts