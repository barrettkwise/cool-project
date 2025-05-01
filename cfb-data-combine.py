import pandas as pd
import pickle
import json
from multiprocessing import Pool, cpu_count
from pathlib import PurePath
import numpy as np

data_from_pickle = pickle.load(open(PurePath("cfb_data_to_transfer.pkl"), "rb"))

RAW_DATA_DIR = data_from_pickle.get("RAW_DATA_DIR")
CLEANED_DATA_DIR = data_from_pickle.get("CLEANED_DATA_DIR")
TOP_LEVEL_DIR = data_from_pickle.get("TOP_LEVEL_DIR")

all_data = pd.read_csv(PurePath(CLEANED_DATA_DIR / "cfb_data.csv"))

cumm_player_data = {}
bad_stat_types = ["YPA", "YPR", "YPC", "AVG", "YPP"]


def work(year: int) -> dict:
    year_player_data = all_data.query("Season == @year").drop(columns=["Season"])
    year_result = {}

    for player_name in year_player_data["Player"].unique():
        player_data = year_player_data.query("Player == @player_name")

        player_id = tuple(set(player_data["PlayerId"].values))[0]
        player_team = tuple(set(player_data["Team"].values))[0]
        player_conference = tuple(set(player_data["Conference"].values))[0]
        category_names = set(player_data["Category"].values)
        player_stats = {
            year: {
                cat if cat not in ["puntReturns", "kickReturns"] else "returns": {}
                for cat in category_names
            }
        }

        for _, row in player_data.iterrows():
            stat_type = row["StatType"]
            if stat_type not in bad_stat_types:
                stat_val = row["Stat"]
                original_category = row["Category"]
                category = (
                    "returns"
                    if original_category in {"puntReturns", "kickReturns"}
                    else original_category
                )
                stat_key = str(stat_type).lower()
                stat_val = float(row["Stat"])

                existing_val = player_stats[year][category].get(stat_key, 0)
                if category == "returns" and stat_key == "long":
                    player_stats[year][category][stat_key] = max(stat_val, existing_val)
                else:
                    player_stats[year][category][stat_key] = existing_val + stat_val

        if player_name not in year_result:
            year_result[player_name] = {
                "player_id": player_id,
                "player_team": player_team,
                "player_conference": player_conference,
                "years_played": 0,
                "player_stats": player_stats,
            }
        else:
            year_result[player_name]["player_stats"].update(player_stats)

    return year_result


def driver_function() -> None:
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(work, range(2004, 2025))

        for year_result in results:
            for player_name, data in year_result.items():
                player_stats = data["player_stats"]
                player_id = data["player_id"]

                try:
                    player_id = int(player_id)
                except (TypeError, ValueError):
                    player_id = None

                if player_name not in cumm_player_data:
                    cumm_player_data[player_name] = {
                        "player_id": player_id,
                        "years_played": 1,
                        "player_stats": player_stats,
                    }
                else:
                    cumm_player_data[player_name]["years_played"] += 1
                    cumm_player_data[player_name]["player_stats"].update(player_stats)

    # Ensure JSON-serializable output
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean(i) for i in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        return obj

    with open(PurePath(CLEANED_DATA_DIR / "cfb_player_data.json"), "w") as f:
        json.dump(clean(cumm_player_data), f, indent=2)


if __name__ == "__main__":
    driver_function()
