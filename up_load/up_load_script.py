import pandas as pd
from pathlib import Path
import json
import numpy as np
from dateutil import parser

file_path = Path("/Users/bernie/code_projects/hay-logger/up_load/hay log book.csv")


the_types = {"1st cutting change":np.int32, "2nd cutting change":np.int32}
df = pd.read_csv(file_path, index_col=False, parse_dates=[1], keep_default_na=False, date_format="%d-%b-%y")
# convert NaN to zeros
df = df.fillna(0)

the_data = []
for index, wip_row in enumerate(df.iterrows(), 1):
    pk = index * 2
    row = wip_row[1]
    django_date = parser.parse(row["date"])
    hay_type = ['1st cutting change', '2nd cutting change']
    hay_num = [1,2]
    # track total number of bails, starting from initial amount
    total = {
        '1': 97,
        '2': 148,
        }
    for hay, num in zip(hay_type, hay_num):
        if row[hay]:
            total[str(num)] += int(row[hay])
            if int(row[hay]) > 0:
                direction = "DEPOSIT"
            else:
                direction = "WITHDRAW"
            log_dict = {}
            log_dict["model"] = "log_app.log"
            log_dict["pk"] = pk - (1- num)
            log_dict["fields"] = {
                "date": django_date.strftime('%Y-%m-%d %H:%M'),
                "hay_type": num,
                "direction": direction,
                "amount": abs(int(row[hay])),
                "notes": row["notes"]
            }
            the_data.append(log_dict)

with open ('up_load/data_to_django.json','w',encoding='utf-8') as f:
    json.dump(the_data, f, ensure_ascii=False, indent=2)

print(f"first cutting total {total['1']}")
print(f"second cutting total {total['2']}")

# requests.get("http://127.0.0.1:8000")
