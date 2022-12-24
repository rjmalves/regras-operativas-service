import pandas as pd
df = pd.read_csv("regras_reservatorios.csv", sep=";")
df = df.loc[~df["COD_RESERVATORIO_VOL"].str.contains("&")]
df = df.astype({"CODIGO_USINA_RESTRICAO": int})
regras = []
for _, linha in df.iterrows():
    regras.append({
        "reservoirCode": linha["COD_RESERVATORIO_VOL"],
        "uheCode": linha["CODIGO_USINA_RESTRICAO"],
        "constraintType": linha["TIPO_REST"],
        "month": linha["MES"],
        "minVolume": linha["VOL_MIN"],
        "maxVolume": linha["VOL_MAX"],
        "minLimit": linha["LIM_MIN"],
        "maxLimit": linha["LIM_MAX"],
        "frequency": linha["PERIOD"],
        "label": linha["LEGENDA_FAIXA"],
    })

import json
with open("regras.json", "w") as arq_json:
    json.dump(regras, arq_json)