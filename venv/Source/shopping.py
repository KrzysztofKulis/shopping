import cv2
import pytesseract
import urllib.request
import sys
import re

def getHtmlFromLink(link):
    html = ""
    try:
        url = urllib.request.urlopen(link)
        mybytes = url.read()
        html = mybytes.decode("utf8")
    except:
        print("Failed to read url: {}! Skipping...".format(link))
    return html

def findTokens(what, where):
    return re.finditer(what, where)

def findIngredients(content: str):
    def findIngredientArea():
        start_index = content.find(start_token)
        if start_index == -1:
            return -1, []

        end_index = content.find(end_token, start_index)
        if end_index == -1:
            return -1, []

        return 0, content[start_index: end_index]

    def getContentBetweenPairedTokens(start_token, end_token, area):
        matches_start_ul = list(findTokens(start_token, area))
        matches_end_ul = list(findTokens(end_token, area))

        ul_content = []
        for i in range(len(matches_start_ul) - 1):
            j = i
            while matches_start_ul[i].end() >  matches_end_ul[j].start():
                j += 1
            ul_content.append(area[matches_start_ul[i].end(): matches_end_ul[j].start()])

        if matches_start_ul[-1].end() >  matches_end_ul[-1].start():
            ul_content.append(area[matches_start_ul[-1].end() : ])
        else:
            ul_content.append(area[matches_start_ul[-1].end(): matches_end_ul[-1].start()])

        return ul_content

    def formatIngredients(ing: list):
        filtered = []
        for i in range(len(ing)):
            line = ing[i].replace("\r", "").replace("\n", "").replace("\t", "").strip()
            if line == "":
                continue
            filtered.append(line)
        return filtered


    start_token = ""
    end_token = ""
    if "kwestiasmaku" in content:
        start_token = "group-skladniki"
        end_token = "group-przepis"
        ingredient_start = "<li>"
        ingredient_end = "</li>"
    # elif "jadlonomia" in content:
    #     start_token = "Skladniki"
    #     end_token = "Przygotowanie"
    elif "weganka" in content:
        start_token = "Składniki"
        end_token = "<div"
        ingredient_start = "\n"
        ingredient_end = "<br />"
    elif "ervegan" in content:
        start_token = "Składniki"
        end_token = "<br> <br>"
        ingredient_start = "<br />"
        ingredient_end = "<br />"

        
    failed = "Failed to find ingredients!"

    rc, ingredient_area = findIngredientArea()
    if rc == -1:
        return []

    if "kwestiasmaku" in content:
        ul_content = getContentBetweenPairedTokens("<ul>", "</ul>", ingredient_area)
        li_content = []
        for ul in ul_content:
            li_content += getContentBetweenPairedTokens("<li>", "</li>", ul)
    elif "weganka" in content:
        pattern = "<br />\n<br />\n"
        start_offset = ingredient_area.find(pattern) + len(pattern)
        li_content = getContentBetweenPairedTokens(ingredient_start, ingredient_end, ingredient_area[start_offset:])
    elif "ervegan" in content:
        pattern = "<br />"
        start_offset = ingredient_area.find(pattern)
        li_content = getContentBetweenPairedTokens(ingredient_start, ingredient_end, ingredient_area[start_offset:])
        for i, line in enumerate(li_content):
            li_content[i] = line.replace("<strong>", "").replace("</strong>", "").replace("&nbsp;", " ").replace("½", "0.5")
    else: # "jadlonomia" in content:
        img = cv2.imread("Scripts/test.png")
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        text = pytesseract.pytesseract.image_to_string(img, "pol")
        li_content_temp = text.splitlines(False)
        li_content = []
        for li in li_content_temp:
            # if li[0].isupper():
            #     continue
            if li == "" or li[0].isupper():
                continue
            li_content.append(li.strip())

    return formatIngredients(li_content)

def filterIngredient(ingredient):

    def seekForIngredientQuantities(ing):
        res = []

        # numbers, fractions, etc.
        numbers = re.finditer("[0-9]+((,|\/|( *[\-\–] *))*[0-9]*)", ingredient)
        for number in numbers:
            res.append([number.start(), number.group()])

        cores = {
            "sztuk": "sztuka",
            "pę": "pęczek",
            "opak": "opakowanie",
            "pusz": "puszka",
            "szkl": "szklanka",
            "szt": "sztuka",
            "kg": "kilogram",
            "kilo": "kilogram",
            "g ": "gram",
            "gram": "gram",
            "łyżk": "łyżka",
            "łyżek": "łyżka",
            "łyżecz": "łyżeczka",
            "litr": "litr",
            "l ": "litr",
            "mał" : "mały",
            "duż" : "duży",
            "śred": "średni",
        }

        for core in cores:
            index = ing.find(core)
            if index != -1:
                res.append([index, cores[core]])

        res.sort()

        return res

    def seekForIngredientNames(ing):
        cores = {
            "cebul": "cebula",
            "por": "por",
            "olej": "olej",
            "oliw": "oliwa",
            "papryk": "papryka",
            "rozmaryn": "rozmaryn",
            "tymian": "tymianek",
            "oregano": "oregano",
            "cayenne": "pieprz cayenne",
            "strącz": "strączki",
            "bulion": "bulion",
            "kapust": "kapusta",
            "jarmuż": "jarmuż",
            "czos": "czosnek",
            "pomidor": "pomidor",
            "sól": "sól",
            "sol": "sól",
            "pieprz": "pieprz",
            "march": "marchew",
            "seler": "seler"
        }
        res = []
        for core in cores:
            index = ing.find(core)
            if index != -1:
                res.append([index, cores[core]])

        return res

    def pairNamesWithQuantities(names, quantities, alternatives):
        res = []

        quantities_copy = quantities
        grouped_quantities = []
        for name in names:
            grouped = ""
            for i, _ in enumerate(quantities_copy):
                if quantities_copy[i][0] < name[0]:
                    grouped += quantities_copy[i][1] + " "
                    quantities_copy[i][0] = int(sys.maxsize)
            grouped_quantities.append(grouped.rstrip())

        if len(names) == len(grouped_quantities):
            for i, name in enumerate(names):
                res.append([names[i][1], grouped_quantities[i]])
        elif len(names) > len(quantities):
            for i, name in enumerate(names):
                res.append([names[i][1], "-"])

        # for alternative in alternatives:


        return res

    def seekForIngredientAlternatives(ing):
        res = []
        numbers = re.finditer("(lub)|((?<![0-9]),)", ing)
        for number in numbers:
            res.append([number.start(), number.group()])

        return res

    def seekForMajorInfo(ing: str):
        res = ing
        start = res.find("(")
        end = res.find(")")
        if start != -1:
            res = res[0: start] + res[end + 1: -1]
        return res

    def seekForIngredientVarieties(ing: str, names, values):
        res = []

        cores = {
            "wędz": "wędzony",
            "dym": "dymiony",
            "suszo": "suszony",
            "sprosz": "sproszkowany",
            "kroj": "krojony",
            "ugotow": "ugotowany",
            "biał": "biały",
            "włosk": "włoski",
        }

        for i, name in enumerate(names):
            grouped = ""
            for core in cores:
                if values != []:
                    if i == len(names) - 1:
                        where = ing[values[i][0] : ]
                    else:
                        where = ing[values[i][0]:values[i + 1][0]]
                else:
                    where = ing

                if core in where:
                    names[i][1] += " " + cores[core]

        return res

    cored = ""

    ingredient = seekForMajorInfo(ingredient)
    ingredient_names = seekForIngredientNames(ingredient)
    quantities = seekForIngredientQuantities(ingredient)
    varieties = seekForIngredientVarieties(ingredient, ingredient_names, quantities)
    alternatives = seekForIngredientAlternatives(ingredient)
    cored = pairNamesWithQuantities(ingredient_names, quantities, alternatives)
    print(cored)


    return cored

def main():
    links = [
        # "https://www.kwestiasmaku.com/przepis/muffiny-bananowe",
        # "https://www.kwestiasmaku.com/zielony_srodek/rabarbar/sernik_z_musem_rabarbarowym/przepis.html",
        # "https://www.weganka.com/2020/04/serowe-tofu-w-marynacie-z-patkow.html",
        # "https://www.weganka.com/2018/07/kotlety-rybne-z-kaszy-jaglanej-tofu-i.html",
        # "https://ervegan.com/2020/03/klopsiki-z-soczewicy-i-kaszy-gryczanej/",
        "https://www.jadlonomia.com/",
    ]

    ingredients = []
    for link in links:
        ingredients += findIngredients(getHtmlFromLink(link))

    ingredients_filtered = []
    for ingredient in ingredients:
        ingredients_filtered += filterIngredient(ingredient)

if __name__ == "__main__":
    main()