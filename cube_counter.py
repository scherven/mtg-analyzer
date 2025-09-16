import marimo

__generated_with = "0.14.17"
app = marimo.App(width="medium")


@app.cell
def _():
    import pandas as pd
    import json
    import requests
    import tabulate as tb
    import numpy as np
    import os
    return json, os, pd, requests, tb


@app.cell
def _(json, pd, requests):
    URL = "https://data.scryfall.io/default-cards/default-cards-20250813211854.json"
    full_scryfall_df = pd.DataFrame(json.loads(requests.get(URL).text))
    full_scryfall_df
    return (full_scryfall_df,)


@app.cell
def _(full_scryfall_df, json, requests):
    df = full_scryfall_df[['name',                       # the name of the card - not technically necessary but helpful for debugging
                           'mana_cost',                  # what type of mana the card costs to summon
                           'cmc',                        # how much mana the card costs
                           'type_line',                  # the type of the card (creature, sorcery, etc)
                           'oracle_text',                # what the card does
                           'power', 'toughness',         # the strength of the card if it's a creature
                           'colors', 'color_identity',   # more info on what type of mana the card costs
                           'keywords',                   # the keywords on the card (more on this later)
                           'set', 'released_at',         # when the card was released
                           'rarity',                     # how much the card was printed
                           'games',                      # games tells if it is legal online or in paper (we exclude online-only cards)
                           'legalities', 'card_faces']]                # which formats the card is legal in

    df = df[df['games'].apply(lambda i: 'paper' in i)]
    df = df.sort_values(by=['name', 'released_at'])
    df = df.drop_duplicates(subset=['name'])
    def legal(legalities):
        v = legalities.values()
        if len(set(v)) == 1 and "not_legal" in v:
            return False
        return True

    df = df[df['legalities'].apply(legal)]
    df = df[~df["type_line"].str.contains("Token", na=False)] # remove tokens
    unsets = ['unglued', 'unhinged', 'unstable', 'unsanctioned', 'unfinity']
    sets = json.loads(requests.get("https://api.scryfall.com/sets").text)
    for s in sets["data"]:
        if s['name'].lower() in unsets or s['code'] == 'sld':
            df = df[~df["set"].str.contains(s['code'])]
    return (df,)


@app.cell
def _(df):
    df
    return


@app.cell
def _(df):
    def load_df(file):
        cards = [i.strip() for i in open(file).readlines() if not i.startswith("#")]
        condition = (
            df['name'].isin(cards) |
            df['name'].str.split('//').str[0].str.strip().isin(cards)  
        )
    
        cube_df = df[condition]
    
        for index, row in cube_df.iterrows():
            card_faces = row['card_faces']
            if isinstance(card_faces, list):
                if 'colors' in card_faces[0]:
                    cube_df.at[index, 'colors'] = card_faces[0]['colors'] 

        return cube_df
    return (load_df,)


@app.function
def filter_df(cube_df, header):
    land_mask = cube_df.type_line.str.contains('Land') & ~cube_df.type_line.str.contains('//', na=False)
    
    if header in "WUBRG":
        return cube_df[cube_df.colors.apply(lambda x: x == [header])]
    elif header == "C":
        colorless_mask = cube_df.colors.apply(lambda x: x == [])
        return cube_df[colorless_mask & ~land_mask]
    elif header == "L":
        return cube_df[land_mask]
    elif header == "M":
        return cube_df[cube_df.colors.apply(lambda x: len(x) > 1)]


@app.cell
def _():
    def count_total_helper(cube_df, header, per):
        return len(filter_df(cube_df, header)) * (per / len(cube_df))

    def count_total(cube_dfs, header, per):
        return round(sum(count_total_helper(i, header, per) for i in cube_dfs) / len(cube_dfs), 2)
    return (count_total,)


@app.cell
def _():
    def count_category_helper(cube_df, category, header, mv, condense, per):
        filtered = filter_df(cube_df, header)
        filtered = filtered[filtered.type_line.str.contains(category[1:], na=False)]

        if condense:
            filtered = filtered[filtered.cmc >= mv]
        else:
            filtered = filtered[filtered.cmc == mv]

        return len(filtered) * (per / len(cube_df))
    

    def count_category(cube_dfs, category, header, mv, condense, per):
        return round(sum(count_category_helper(i, category, header, mv, condense, per) for i in cube_dfs) / len(cube_dfs), 2)
    return (count_category,)


@app.cell
def _(count_category, count_total, load_df, os, tb):
    # def display_averages(cube_dfs, per=100)

    cube_dfs = []
    for a, b, c in os.walk("cubes"):
        for file in c:
            cube_dfs.append(load_df(f"cubes/{file}"))

    per = 540

    headers = [per, "W", "U", "B", "R", "G", "C", "M", "L"]
    categories = ["creature", "planeswalker", "instant", "sorcery", "artifact", "enchantment"]
    condense = [8, 0, 4, 4, 4, 4]

    rows = []

    def make_row(label, fn):
        return [label] + [fn(i) for i in headers[1:]]

    # total
    rows.append(make_row("total", lambda i: count_total(cube_dfs, i, per)))

    # categories
    for category, limit in zip(categories, condense):
        rows.append(make_row(category, lambda i: count_category(cube_dfs, category, i, 0, True, per)))

        for i in range(limit):
            rows.append(make_row(f"{category} ({i})", lambda j: count_category(cube_dfs, category, j, i, False, per)))

        if limit != 0:
            rows.append(make_row(f"{category} ({limit})+", lambda i: count_category(cube_dfs, category, i, limit, True, per)))

    print(tb.tabulate(rows, headers, tablefmt="outline"))
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
