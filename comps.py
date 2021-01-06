import json

# JSON data taken from https://www.epa.gov/energy/greenhouse-gases-equivalencies-calculator-calculations-and-references

# open json file
with open('./carbon.json', 'r') as fp:
    carbon = json.load(fp)

def calculateImpact(savings):
    comps = []
    for comp in carbon:
        amount = round((float(savings) / float(carbon[comp]['co2'])), 2)
        comps.append({
            "co2": amount,
            "msg": carbon[comp]['msg']
        })
    return comps